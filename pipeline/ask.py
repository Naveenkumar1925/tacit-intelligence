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
                    OLLAMA_BASE_URL, LLM_MODEL, EMBED_MODEL)
from resolve import find_mentions

TOP_K = 8
MAX_TEXT_EVIDENCE = 5
CONFIDENCE_THRESHOLD = 0.45
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
WITH dense, sparse
// anchors: tags named in the question + equipment mentioned by top dense seeds
UNWIND (CASE WHEN size(dense) = 0 THEN [null] ELSE dense[..3] END) AS d
OPTIONAL MATCH (:Chunk {chunk_id: d.id})-[:MENTIONS]->(me:Equipment)
WITH dense, sparse,
     [t IN collect(DISTINCT me.tag) WHERE t IS NOT NULL] + $tags AS anchor_tags
UNWIND (CASE WHEN size(anchor_tags) = 0 THEN [null] ELSE anchor_tags END) AS tag
OPTIONAL MATCH (e:Equipment {tag: tag})
WITH dense, sparse, collect(DISTINCT e) AS anchors
RETURN dense, sparse,
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
    procedures: [(p:Procedure)-[:APPLIES_TO]->(e) | p.sop_id],
    siblings: [(:Area)-[:CONTAINS]->(s:Equipment)
               WHERE s.iso14224_class = e.iso14224_class AND s.tag <> e.tag |
      {tag: s.tag, criticality: s.criticality,
       codes: [(sw:WorkOrder)-[:PERFORMED_ON]->(s) WHERE sw.type = 'corrective' |
               head([(sw)-[:RESULTED_IN]->(sf:FailureMode) | sf.code])]}]
  }] AS graph
"""


def ollama(path, payload, timeout=300):
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


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


def classify_intent(question, tags):
    """Set the blend ratio, never an exclusive branch (spec 10)."""
    if tags:
        return "equipment-anchored", {"text": 0.4, "graph": 0.6}
    if re.search(r"\b(how|what|when|why|procedure|steps?|interval|should)\b",
                 question, re.I):
        return "procedural", {"text": 0.7, "graph": 0.3}
    return "general", {"text": 0.5, "graph": 0.5}


def build_evidence(fused, graph, blend):
    """Number the evidence blocks; return (blocks, citations)."""
    blocks, citations = [], []

    def add(kind, label, text, **meta):
        n = len(blocks) + 1
        blocks.append(f"[{n}] {label}\n{text}")
        citations.append({"n": n, "kind": kind, "label": label, **meta})
        return n

    n_text = MAX_TEXT_EVIDENCE if blend["text"] >= 0.5 else 3
    for f in fused[:n_text]:
        c = f["item"]
        add("chunk", f"{c['doc']} page {c['page']}", c["text"][:1200],
            doc=c["doc"], page=c["page"], chunk_id=c["id"], score=round(f["rrf"], 4))

    for eq in graph:
        if not eq or not eq.get("tag"):
            continue
        hop = 0 if eq.get("anchored") else 1
        wos = sorted(eq["work_orders"], key=lambda w: w["date"], reverse=True)
        corr = [w for w in wos if w["type"] == "corrective"][:8]
        if corr:
            lines = "\n".join(
                f"  {w['date']}  {w['code'] or '-'}  {w['hrs']}h  {w['desc'][:90]}"
                for w in corr)
            add("history", f"{eq['tag']} corrective work order history "
                f"(class {eq['class']}, criticality {eq['criticality']})",
                lines, tag=eq["tag"], hop=hop,
                wo_ids=[w["wo_id"] for w in corr])
        for t in eq["tacit"][:4]:
            add("tacit", f"Operator knowledge ({t['lang']} audio {t['audio']} "
                f"@ {t['t_start']:.0f}s)", t["text"],
                audio=t["audio"], t_start=t["t_start"], lang=t["lang"],
                claim_id=t["claim_id"], hop=hop)
        if eq["siblings"] and eq.get("anchored"):
            sib_lines = "\n".join(
                f"  {s['tag']} (criticality {s['criticality']}) past failure modes: "
                f"{sorted(set(c for c in s['codes'] if c)) or 'none'}"
                for s in eq["siblings"])
            add("siblings", f"Same-class equipment as {eq['tag']} ({eq['class']})",
                sib_lines, tag=eq["tag"], hop=2)
    return blocks, citations


def synthesise(question, blocks):
    prompt = (
        "You are the plant knowledge assistant. Answer the question using ONLY the "
        "numbered evidence below. Every sentence of your answer MUST end with its "
        "citation marker(s) like [1] or [2][3]. Be specific: dates, counts, hours. "
        f"If the evidence does not contain the answer, reply exactly: {ABSTAIN_TEXT}\n\n"
        + "\n\n".join(blocks)
        + f"\n\nQuestion: {question}\nAnswer:"
    )
    out = ollama("/api/chat", {
        "model": LLM_MODEL, "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1},
    })
    return out["message"]["content"].strip()


def confidence(answer, fused, dense, sparse):
    top_dense = dense[0]["score"] if dense else 0.0           # cosine, already 0..1
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
    cited = sum(1 for s in sentences if re.search(r"\[\d+\]", s))
    frac = cited / len(sentences) if sentences else 0.0
    d_ids = {d["id"] for d in dense[:TOP_K]}
    s_ids = {s["id"] for s in sparse[:TOP_K]}
    overlap = len(d_ids & s_ids) / max(1, min(len(d_ids), len(s_ids))) if s_ids else 0.0
    return round(0.4 * top_dense + 0.3 * frac + 0.3 * overlap, 3), {
        "top_dense": round(top_dense, 3), "cited_fraction": round(frac, 3),
        "bm25_dense_overlap": round(overlap, 3)}


_driver = None

def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def ask(question):
    t0 = time.time()
    keys = find_mentions(question)
    with get_driver().session(database=NEO4J_DATABASE) as s:
        register = {r["key"]: r["tag"] for r in s.run(
            "MATCH (e:Equipment) RETURN replace(e.tag,'-','') AS key, e.tag AS tag")}
        tags = sorted({register[k] for k in keys if k in register})
        qvec = ollama("/api/embed", {"model": EMBED_MODEL, "input": [question]}
                      )["embeddings"][0]
        rec = s.run(RETRIEVAL_QUERY, qvec=qvec, ftq=lucene_sanitise(question),
                    tags=tags, k=TOP_K).single()
    dense, sparse, graph = rec["dense"], rec["sparse"], rec["graph"]

    intent, blend = classify_intent(question, tags)
    fused = rrf_fuse(dense, sparse)
    blocks, citations = build_evidence(fused, graph, blend)

    if not blocks:
        return {"answer": ABSTAIN_TEXT, "abstained": True, "confidence": 0.0,
                "confidence_parts": {}, "citations": [], "intent": intent,
                "tags": tags, "elapsed_s": round(time.time() - t0, 2),
                "query": RETRIEVAL_QUERY}

    answer = synthesise(question, blocks)
    conf, parts = confidence(answer, fused, dense, sparse)
    abstained = ABSTAIN_TEXT.lower() in answer.lower() or conf < CONFIDENCE_THRESHOLD
    if conf < CONFIDENCE_THRESHOLD and ABSTAIN_TEXT.lower() not in answer.lower():
        answer = (f"{ABSTAIN_TEXT} (Confidence {conf} is below the "
                  f"{CONFIDENCE_THRESHOLD} threshold; refusing to guess.)")
    used = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    return {
        "answer": answer, "abstained": abstained,
        "confidence": conf, "confidence_parts": parts,
        "citations": [c for c in citations if c["n"] in used] or citations,
        "intent": intent, "blend": blend, "tags": tags,
        "elapsed_s": round(time.time() - t0, 2),
        "query": RETRIEVAL_QUERY,
    }


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
