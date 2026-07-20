"""P3 Ask agent: question -> cited answer with computed confidence (spec 8 P3, 10).

Run:  py pipeline/ask.py "P-101A keeps tripping on high vibration - has this happened before?"

Design (spec):
  Entry   - exact tag match anchors directly; BM25 + dense always both run and
            fuse via RRF (score = sum 1/(60+rank)). Intent sets the blend ratio,
            never an exclusive branch.
  Expand  - 2 hops from anchors inside the SAME Cypher round trip:
            equipment -> work orders -> failure modes -> siblings -> tacit.
  Rank    - text by RRF; graph facts by hop distance (0: anchor, 1: history, 2: siblings).
  Synth   - every claim carries [n] resolving to doc+page or audio timestamp.
  Confidence = 0.4*top_dense + 0.3*cited_sentence_fraction + 0.3*bm25/dense overlap.
  Below threshold -> abstain ("not present in the corpus" is the correct answer).

ask_stream() yields the same answer token-by-token for the UI (SSE); ask() is the
blocking form. `mode` supports the eval ablations: full | dense | bm25 | no_graph.
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).parent))
from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
                    OLLAMA_BASE_URL, LLM_MODEL, EMBED_MODEL, STANDARDS_PACK)
from resolve import find_mentions

TOP_K = 8
MAX_TEXT_EVIDENCE = 5
MAX_CHUNK_CHARS = 2800          # full chunk: truncating cut SOP-114's interval line
MAX_ANSWER_TOKENS = 350
LLM_OPTIONS = {"temperature": 0.1, "num_predict": MAX_ANSWER_TOKENS,
               "num_ctx": 6144}  # 4096 silently clips long evidence prompts
CONFIDENCE_THRESHOLD = 0.45     # display threshold; uncited answers below it abstain
FORCE_ABSTAIN_BELOW = 0.30      # even cited answers abstain under this
ABSTAIN_TEXT = "Not present in the corpus."

# one round trip: dense seeds + BM25 seeds + 2-hop expansion from anchors
RETRIEVAL_QUERY = """
CALL () {
  CALL db.index.vector.queryNodes('chunk_embedding', $k, $qvec)
  YIELD node, score
  RETURN collect({id: node.chunk_id, text: node.text, doc: node.doc_id,
                  page: node.page, score: score}) AS dense
}
CALL () {
  CALL db.index.fulltext.queryNodes('chunk_text', $ftq, {limit: $k})
  YIELD node, score
  RETURN collect({id: node.chunk_id, text: node.text, doc: node.doc_id,
                  page: node.page, score: score}) AS sparse
}
CALL () {
  CALL db.index.vector.queryNodes('clause_embedding', 3, $qvec)
  YIELD node, score
  RETURN collect({clause_id: node.clause_id, title: node.title, text: node.text,
                  page: node.page, score: score}) AS sim_clauses
}
CALL () {
  MATCH (cl:Clause) WHERE cl.clause_id IN $clause_ids
  RETURN collect({clause_id: cl.clause_id, title: cl.title, text: cl.text,
                  page: cl.page, score: 1.0}) AS exact_clauses
}
WITH dense, sparse, sim_clauses, exact_clauses
// anchors: tags named in the question + equipment mentioned by top dense seeds
UNWIND (CASE WHEN size(dense) = 0 THEN [null] ELSE dense[..3] END) AS d
OPTIONAL MATCH (:Chunk {chunk_id: d.id})-[:MENTIONS]->(me:Equipment)
WITH dense, sparse, sim_clauses, exact_clauses,
     [t IN collect(DISTINCT me.tag) WHERE t IS NOT NULL] + $tags AS anchor_tags
UNWIND (CASE WHEN size(anchor_tags) = 0 THEN [null] ELSE anchor_tags END) AS tag
OPTIONAL MATCH (e:Equipment {tag: tag})
WITH dense, sparse, sim_clauses, exact_clauses, collect(DISTINCT e) AS anchors
RETURN dense, sparse, sim_clauses, exact_clauses,
  [e IN anchors | {
    tag: e.tag, class: e.iso14224_class, criticality: e.criticality,
    aliases: e.aliases, service: e.service,
    anchored: e.tag IN $tags,
    work_orders: [(w:WorkOrder)-[:PERFORMED_ON]->(e) |
      {wo_id: w.wo_id, date: toString(w.date), type: w.type,
       hrs: w.downtime_hrs, desc: w.description, tech: w.technician,
       code: head([(w)-[:RESULTED_IN]->(f:FailureMode) | f.code])}],
    tacit: [(t:TacitKnowledge)-[:APPLIES_TO]->(e) |
      {claim_id: t.claim_id, text: t.text, lang: t.lang, audio: t.audio_id,
       t_start: t.t_start, type: t.claim_type}],
    inspections: [(i:InspectionRecord)-[:ON]->(e) |
      {record_id: i.record_id, date: toString(i.date), result: i.result,
       valid_until: toString(i.valid_until)}],
    ncrs: [(x:NCR)-[:AGAINST]->(e) |
      {ncr_id: x.ncr_id, date: toString(x.date), description: x.description,
       status: x.status,
       clause: head([(x)-[:CITES]->(c:Clause) | c.clause_id])}],
    kpis: [(q:QualityKPI)-[:FOR]->(e) |
      {process_id: q.process_id, metric: q.metric, period: q.period,
       value: q.value,
       descr: head([(q)-[:OF]->(p:Process) | p.description])}],
    procedures: [(p:Procedure)-[:APPLIES_TO]->(e) | p.sop_id],
    siblings: [(:Area)-[:CONTAINS]->(s:Equipment)
               WHERE s.iso14224_class = e.iso14224_class AND s.tag <> e.tag |
      {tag: s.tag, criticality: s.criticality,
       codes: [(sw:WorkOrder)-[:PERFORMED_ON]->(s) WHERE sw.type = 'corrective' |
               head([(sw)-[:RESULTED_IN]->(sf:FailureMode) | sf.code])]}]
  }] AS graph
"""

_driver = None
_register = None            # canonical-key -> tag, cached per process


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD),
                                       notifications_min_severity="OFF")
    return _driver


def get_register(session):
    global _register
    if not _register:
        items = session.run(
            "MATCH (a:Area)-[:CONTAINS]->(e:Equipment) "
            "RETURN replace(e.tag,'-','') AS key, e.tag AS tag, "
            "e.iso14224_class AS klass, a.name AS area").data()
        processes = session.run(
            "MATCH (p:Process) RETURN p.process_id AS pid, "
            "p.description AS descr, p.tag AS tag").data()
        _register = {"by_key": {r["key"]: r["tag"] for r in items},
                     "items": items, "processes": processes}
    return _register


# class/area phrases resolve to equipment sets when a history-shaped question
# names no tag ("have any heat exchangers overheated?") — without this, such
# questions get procedure text only and wrongly abstain
CLASS_PHRASES = [("heat exchanger", "heat_exchanger"), ("exchanger", "heat_exchanger"),
                 ("control valve", "control_valve"), ("valve", "control_valve"),
                 ("pump", "centrifugal_pump")]
AREA_PHRASES = {"process area": "Area-1", "area-1": "Area-1", "area 1": "Area-1",
                "utilities area": "Area-2", "utility area": "Area-2",
                "area-2": "Area-2", "area 2": "Area-2"}
HISTORY_SHAPE_RE = re.compile(
    r"\b(fail|failure|history|happened|problem|issue|downtime|trip|broke|"
    r"repeat|repair|corrective|inspect|expired|maintenance record)", re.I)

# QMS retrieval router: clause references and quality/analytics intent
CLAUSE_NUM_RE = re.compile(r"\b(\d+\.\d+(?:\.\d+)?)\b")
QUALITY_RE = re.compile(
    r"\b(cpk|cp k|ppm|capab|in control|out of control|defect|quality|clause|"
    r"nonconform|ncr|audit|complian|standard requirement)\b", re.I)


def process_anchor_tags(question, register):
    """PRC ids or process descriptions ('feed flow control') anchor equipment.

    Matches the id, the full description, or its two-word prefix — 'the feed
    transfer process' must reach 'Feed transfer to Process Area'."""
    q = question.lower()
    tags, pids = [], []
    for p in register.get("processes", []):
        descr = (p["descr"] or "").lower()
        prefix = " ".join(descr.split()[:2])
        if (p["pid"].lower() in q or (descr and descr in q)
                or (len(prefix.split()) == 2 and prefix in q)):
            tags.append(p["tag"])
            pids.append(p["pid"])
    return tags, pids


def class_anchor_tags(question, register):
    if not HISTORY_SHAPE_RE.search(question) and not detect_modes(question):
        return []
    q = question.lower()
    klasses = set()
    for phrase, klass in CLASS_PHRASES:
        if phrase in q:
            klasses.add(klass)
            break                       # phrases are ordered most-specific first
    areas = {a for p, a in AREA_PHRASES.items() if p in q}
    if not klasses and not areas:
        return []
    return sorted(r["tag"] for r in register["items"]
                  if (not klasses or r["klass"] in klasses)
                  and (not areas or r["area"] in areas))


def ollama(path, payload, timeout=300):
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ollama_chat_stream(prompt):
    """Yield content tokens from a streaming chat call."""
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps({"model": LLM_MODEL, "stream": True,
                         "messages": [{"role": "user", "content": prompt}],
                         "options": LLM_OPTIONS}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            if not line.strip():
                continue
            chunk = json.loads(line)
            tok = chunk.get("message", {}).get("content", "")
            if tok:
                yield tok
            if chunk.get("done"):
                return


def lucene_sanitise(q):
    q = re.sub(r'[+\-!(){}\[\]^"~*?:\\/]|&&|\|\|', " ", q)
    terms = [t for t in q.split() if t.upper() not in ("AND", "OR", "NOT") and len(t) > 1]
    return " OR ".join(terms) if terms else "plant"


def rrf_fuse(dense, sparse):
    scores = {}
    for lst in (dense, sparse):
        for rank, item in enumerate(lst):
            scores.setdefault(item["id"], {"item": item, "rrf": 0.0})
            scores[item["id"]]["rrf"] += 1.0 / (60 + rank)
    return sorted(scores.values(), key=lambda x: -x["rrf"])


SYMPTOM_MODES = {          # question wording -> ISO 14224 failure mode
    "VIB": ["vibration", "vibrat", "shaking"],
    "SER": ["seal"],
    "BRG": ["bearing"],
    "PLU": ["strainer", "plug", "chok", "blocked", "suction pressure"],
    "LEK": ["leak"],
    "OHE": ["overheat", "running hot", "temperature high"],
    "ELP": ["electrical", "overload", "contactor"],
}


def detect_modes(question):
    q = question.lower()
    return [m for m, kws in SYMPTOM_MODES.items() if any(k in q for k in kws)]


def classify_intent(question, tags):
    """Set the blend ratio, never an exclusive branch (spec 10)."""
    if tags:
        return "equipment-anchored", {"text": 0.4, "graph": 0.6}
    if re.search(r"\b(how|what|when|why|procedure|steps?|interval|should)\b",
                 question, re.I):
        return "procedural", {"text": 0.7, "graph": 0.3}
    return "general", {"text": 0.5, "graph": 0.5}


def build_evidence(fused, graph, blend, modes=(), clauses=(), quality=False):
    """Number the evidence blocks; return (blocks, citations)."""
    blocks, citations = [], []

    def add(kind, label, text, **meta):
        n = len(blocks) + 1
        # [E1]-style markers: plain [1] collides with the SOPs' own numbered
        # sections and the model starts citing section numbers instead
        blocks.append(f"[E{n}] {label}\n{text}")
        citations.append({"n": n, "kind": kind, "label": label, **meta})
        return n

    def add_chunks():
        n_text = MAX_TEXT_EVIDENCE if blend["text"] >= 0.5 else 3
        if quality:
            n_text = 2          # analytics questions: computed evidence leads
        for f in fused[:n_text]:
            c = f["item"]
            add("chunk", f"{c['doc']} page {c['page']}", c["text"][:MAX_CHUNK_CHARS],
                doc=c["doc"], page=c["page"], chunk_id=c["id"],
                score=round(f["rrf"], 4))

    def add_graph():
        # full history + siblings only for equipment the question anchored
        # (named tags, or class/area phrases on history-shaped questions);
        # mention-derived equipment contributes operator knowledge only — a wall
        # of unrelated histories drowns the answer and pollutes citations
        n_anchored = sum(1 for e in graph if e and e.get("anchored"))
        row_cap = 8 if n_anchored <= 2 else 4
        for eq in sorted((e for e in graph if e and e.get("tag")),
                         key=lambda e: not e.get("anchored")):
            hop = 0 if eq.get("anchored") else 1
            if eq.get("anchored"):
                # rows matching the failure mode the question asked about go
                # first — a relevant event at the bottom of a long table gets
                # overlooked by the model (verified failure case: VIB row 7 of 7)
                wos = sorted(eq["work_orders"], key=lambda w: w["date"], reverse=True)
                wos = sorted(wos, key=lambda w: w["code"] not in modes)  # stable
                corr = [w for w in wos if w["type"] == "corrective"][:row_cap]
                if corr:
                    label = (f"{eq['tag']} corrective work order history "
                             f"(class {eq['class']}, criticality {eq['criticality']})")
                    if modes and any(w["code"] in modes for w in corr):
                        label += f" — {'/'.join(modes)} events listed first"
                    lines = "\n".join(
                        f"  {w['date']}  {w['code'] or '-'}  {w['hrs']}h  {w['desc'][:90]}"
                        for w in corr)
                    add("history", label, lines, tag=eq["tag"], hop=hop,
                        wo_ids=[w["wo_id"] for w in corr])
                if eq.get("inspections"):
                    today = time.strftime("%Y-%m-%d")
                    insp_lines = "\n".join(
                        f"  {i['record_id']}  {i['date']}  {i['result'][:70]}  "
                        f"valid until {i['valid_until']}"
                        f"{'  ** EXPIRED **' if i['valid_until'] < today else ''}"
                        for i in eq["inspections"])
                    add("inspection", f"{eq['tag']} inspection records", insp_lines,
                        tag=eq["tag"], hop=hop,
                        record_ids=[i["record_id"] for i in eq["inspections"]])
                if eq["siblings"] and n_anchored <= 2:
                    sib_lines = "\n".join(
                        f"  {s['tag']} (criticality {s['criticality']}) past failure "
                        f"modes: {sorted(set(c for c in s['codes'] if c)) or 'none'}"
                        for s in eq["siblings"])
                    add("siblings", f"Same-class equipment as {eq['tag']} "
                        f"({eq['class']})", sib_lines, tag=eq["tag"], hop=2)
            for t in eq["tacit"][:4 if eq.get("anchored") else 2]:
                add("tacit", f"Operator knowledge ({t['lang']} audio {t['audio']} "
                    f"@ {t['t_start']:.0f}s)", t["text"],
                    audio=t["audio"], t_start=t["t_start"], lang=t["lang"],
                    claim_id=t["claim_id"], hop=hop)

    def add_clauses():
        for cl in clauses:
            add("clause", f"{STANDARDS_PACK['std_id']} clause {cl['clause_id']} "
                f"— {cl['title']}", cl["text"][:1500],
                clause_id=cl["clause_id"], page=cl["page"],
                doc=STANDARDS_PACK["std_id"], score=round(cl["score"], 3))

    def add_quality():
        # computed KPIs + clause-linked NCRs for anchored equipment. Emitted
        # FIRST for analytics questions: the computed flag IS the answer, and
        # buried mid-prompt the model hedges around it (verified failure)
        if not quality:
            return
        for eq in graph:
            if not eq or not eq.get("tag") or not eq.get("anchored"):
                continue
            if eq.get("kpis"):
                by_pm = {}
                for k in eq["kpis"]:
                    by_pm.setdefault((k["process_id"], k["metric"]), []).append(k)
                kpi_lines = []
                for (pid, metric), vals in sorted(by_pm.items()):
                    descr = vals[0].get("descr") or ""
                    vals.sort(key=lambda k: k["period"])
                    series = " | ".join(f"{v['period']}={v['value']}"
                                        for v in vals[-4:])
                    flag = ""
                    d = STANDARDS_PACK["kpi_defs"].get(metric, {})
                    if metric == "CPK" and vals[-1]["value"] < d.get("min", 0):
                        flag = (f"   -> BELOW {d['min']} MINIMUM: NOT CAPABLE "
                                "(clause 9.1)")
                    if (metric == "PPM" and len(vals) >= 3 and
                            vals[-1]["value"] > vals[-2]["value"]
                            > vals[-3]["value"]):
                        flag = ("   -> RISING 3 CONSECUTIVE MONTHS: "
                                "INVESTIGATE (clause 9.1)")
                    kpi_lines.append(
                        f"  {pid} ({descr} process) {metric}: {series}{flag}")
                add("kpi", f"{eq['tag']} computed quality KPIs "
                    "(structured store — computed, never embedded)",
                    "\n".join(kpi_lines), tag=eq["tag"], hop=0,
                    query="MATCH (q:QualityKPI {tag: $tag}) RETURN q.process_id,"
                          " q.metric, q.period, q.value ORDER BY q.period")
            if eq.get("ncrs"):
                ncr_lines = "\n".join(
                    f"  {n['ncr_id']}  {n['date']}  [{n['status']}] clause "
                    f"{n['clause']}: {n['description'][:110]}"
                    for n in sorted(eq["ncrs"], key=lambda n: n["date"],
                                    reverse=True)[:4])
                add("ncr", f"{eq['tag']} nonconformance register "
                    "(clause-linked)", ncr_lines, tag=eq["tag"], hop=1,
                    ncr_ids=[n["ncr_id"] for n in eq["ncrs"][:4]])

    # computed analytics first (they ARE the answer for capability/trend
    # questions), then clauses, then spec 8 ordering: graph facts lead for
    # equipment-anchored questions, text leads otherwise
    add_quality()
    add_clauses()
    if blend["graph"] >= 0.5:
        add_graph()
        add_chunks()
    else:
        add_chunks()
        add_graph()
    return blocks, citations


def synthesis_prompt(question, blocks):
    return (
        "You are the plant knowledge assistant. Answer the question using ONLY the "
        "evidence below, which is numbered [E1], [E2], ... Every sentence of your "
        "answer MUST end with the marker(s) of the evidence that directly supports "
        "it, like [E1] or [E2][E3] — never a blanket list, and never numbers that "
        "are not evidence markers. Be specific: dates, counts, hours. Related "
        "records ARE the answer even when wording differs — a vibration work "
        "order answers a vibration question; report the closest documented "
        "events rather than abstaining when directly relevant records exist. "
        "Answer the question as asked, summarising the matching records plainly. "
        "Evidence marked 'computed' is an authoritative calculation from the "
        "structured quality store: flags such as NOT CAPABLE or RISING are the "
        "direct answer to capability and trend questions — state them as the "
        "answer with their numbers, do not hedge around them. "
        f"If the evidence does not contain the answer, reply exactly: {ABSTAIN_TEXT}\n\n"
        + "\n\n".join(blocks)
        + f"\n\nQuestion: {question}\nAnswer:"
    )


def confidence(answer, fused, dense, sparse):
    # top retrieval: dense cosine is already 0..1; BM25 (ablation runs) squashed
    if dense:
        top = dense[0]["score"]
    elif sparse:
        top = min(1.0, sparse[0]["score"] / 8.0)
    else:
        top = 0.0
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
    cited = sum(1 for s in sentences if re.search(r"\[E\d+\]", s))
    frac = cited / len(sentences) if sentences else 0.0
    d_ids = {d["id"] for d in dense[:TOP_K]}
    s_ids = {s["id"] for s in sparse[:TOP_K]}
    overlap = len(d_ids & s_ids) / max(1, min(len(d_ids), len(s_ids))) if s_ids else 0.0
    # overlap is structurally noisy on a small corpus — weight it lightly, or
    # correct cited answers get pushed under the abstain threshold
    return round(0.5 * top + 0.4 * frac + 0.1 * overlap, 3), {
        "top_dense": round(top, 3), "cited_fraction": round(frac, 3),
        "bm25_dense_overlap": round(overlap, 3)}


def _retrieve(question, mode="full"):
    """Shared retrieval + evidence assembly. Returns a working dict."""
    t0 = time.time()
    with get_driver().session(database=NEO4J_DATABASE) as s:
        register = get_register(s)
        by_key = register["by_key"]
        tags = sorted({by_key[k] for k in find_mentions(question) if k in by_key})
        proc_tags, proc_ids = process_anchor_tags(question, register)
        tags = sorted(set(tags) | set(proc_tags))
        if not tags:
            tags = class_anchor_tags(question, register)
        clause_ids = CLAUSE_NUM_RE.findall(question)
        quality = bool(QUALITY_RE.search(question) or clause_ids or proc_ids)
        qvec = ollama("/api/embed", {"model": EMBED_MODEL, "input": [question]}
                      )["embeddings"][0]
        rec = s.run(RETRIEVAL_QUERY, qvec=qvec, ftq=lucene_sanitise(question),
                    tags=tags, clause_ids=clause_ids, k=TOP_K).single()
    dense, sparse, graph = rec["dense"], rec["sparse"], rec["graph"]

    # router: exact clause references always surface; similar clauses join when
    # the question is quality-shaped or similarity is unambiguous
    clauses, seen = [], set()
    for cl in list(rec["exact_clauses"]) + [
            c for c in rec["sim_clauses"] if quality or c["score"] >= 0.80]:
        if cl["clause_id"] not in seen:
            seen.add(cl["clause_id"])
            clauses.append(cl)
    clauses = clauses[:3]

    # ablation modes for the eval harness (spec Day 3): starve one leg and
    # re-rank honestly with what remains
    if mode == "dense":
        sparse = []
    elif mode == "bm25":
        dense = []
    elif mode == "no_graph":
        graph = []

    intent, blend = classify_intent(question, tags)
    if quality and intent == "general":
        intent = "quality"
    modes = detect_modes(question)
    fused = rrf_fuse(dense, sparse)
    blocks, citations = build_evidence(fused, graph, blend, modes,
                                       clauses=clauses, quality=quality)
    return {"t0": t0, "tags": tags, "dense": dense, "sparse": sparse,
            "graph": graph, "intent": intent, "blend": blend, "modes": modes,
            "fused": fused, "blocks": blocks, "citations": citations}


def _finalise(question, answer, w):
    conf, parts = confidence(answer, w["fused"], w["dense"], w["sparse"])
    used = {int(n) for n in re.findall(r"\[E(\d+)\]", answer)}
    model_abstained = ABSTAIN_TEXT.lower() in answer.lower()
    # a substantive, cited answer stands on its own — force abstain only when
    # the answer carries no citations at all or confidence collapses entirely
    forced = (not model_abstained) and (
        conf < FORCE_ABSTAIN_BELOW or (not used and conf < CONFIDENCE_THRESHOLD))
    if forced:
        answer = (f"{ABSTAIN_TEXT} (Confidence {conf} is too low; "
                  "refusing to guess.)")
        used = set()
    abstained = model_abstained or forced
    return {
        "answer": answer, "abstained": abstained,
        "confidence": conf, "confidence_parts": parts,
        "citations": [c for c in w["citations"] if c["n"] in used] or w["citations"],
        "intent": w["intent"], "blend": w["blend"], "tags": w["tags"],
        "elapsed_s": round(time.time() - w["t0"], 2),
        "query": RETRIEVAL_QUERY,
    }


def ask(question, mode="full"):
    w = _retrieve(question, mode)
    if not w["blocks"]:
        return {"answer": ABSTAIN_TEXT, "abstained": True, "confidence": 0.0,
                "confidence_parts": {}, "citations": [], "intent": w["intent"],
                "tags": w["tags"], "elapsed_s": round(time.time() - w["t0"], 2),
                "query": RETRIEVAL_QUERY}
    out = ollama("/api/chat", {
        "model": LLM_MODEL, "stream": False,
        "messages": [{"role": "user",
                      "content": synthesis_prompt(question, w["blocks"])}],
        "options": LLM_OPTIONS,
    })
    return _finalise(question, out["message"]["content"].strip(), w)


def ask_stream(question):
    """Generator of SSE-ready dicts: {'type':'token'|'final', ...}."""
    w = _retrieve(question)
    if not w["blocks"]:
        yield {"type": "final", **_finalise(question, ABSTAIN_TEXT, w)}
        return
    parts = []
    for tok in ollama_chat_stream(synthesis_prompt(question, w["blocks"])):
        parts.append(tok)
        yield {"type": "token", "text": tok}
    yield {"type": "final", **_finalise(question, "".join(parts).strip(), w)}


def prewarm():
    """Load models + register cache so the first demo question is warm."""
    with get_driver().session(database=NEO4J_DATABASE) as s:
        get_register(s)
    ollama("/api/embed", {"model": EMBED_MODEL, "input": ["warm"]})
    ollama("/api/chat", {"model": LLM_MODEL, "stream": False,
                         "messages": [{"role": "user", "content": "Say OK."}],
                         "options": {"num_predict": 5}})
    return "warm"


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or \
        "P-101A keeps tripping on high vibration - has this happened before?"
    r = ask(q)
    print(f"Q: {q}\n")
    print(r["answer"])
    print(f"\nconfidence={r['confidence']} {r['confidence_parts']} "
          f"intent={r['intent']} tags={r['tags']} elapsed={r['elapsed_s']}s")
    for c in r["citations"]:
        print(f"  [{c['n']}] ({c['kind']}) {c['label']}")
