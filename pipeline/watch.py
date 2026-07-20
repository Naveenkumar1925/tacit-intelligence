"""P4 Watch agent: failure-pattern detection + divergence (spec 8 P4).

Run:  py pipeline/watch.py            one detection sweep, writes :Alert nodes
      py pipeline/watch.py --dry      compute and print, write nothing

Detection is arithmetic + Cypher only; the LLM writes the human narrative
afterwards. That separation keeps every finding defensible.

  overdue   : MTBF from gaps between same-mode corrective failures;
              risk_ratio = days_since_last / mtbf, alert above 0.8
  chronic   : same mode >= 3 times inside 12 months
  siblings  : recent failure -> same-class equipment, split into confirmed
              history vs needs-preventive-check
  divergence: same-topic gate first (shared equipment via APPLIES_TO + shared
              activity keyword + embedding cosine), only then compare stated
              frequencies. Never embedding similarity alone (spec 8).

Business impact per alert: avoidable downtime = historical mean downtime_hrs of
that failure mode on that equipment class (spec 9's downtime-avoided figure).
"""

import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).parent))
from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
                    OLLAMA_BASE_URL, LLM_MODEL,
                    RISK_RATIO_THRESHOLD, CHRONIC_COUNT, CHRONIC_WINDOW_DAYS)

TODAY = date.today                       # callable so tests can monkeypatch
SIBLING_RECENT_DAYS = 45                 # a failure this recent triggers sibling review
DIVERGENCE_COSINE_GATE = 0.60

FREQ_PATTERNS = [
    (r"\bdaily\b|\bevery day\b", 1),
    (r"\bweekly\b|\bevery week\b", 7),
    (r"\bfortnightly\b|\bevery (?:two|2) weeks?\b|\bevery fortnight\b|\btwice a month\b", 14),
    (r"\bmonthly\b|\bevery month\b|\bonce a month\b", 30),
    (r"\bquarterly\b|\bevery (?:three|3) months?\b", 91),
    (r"\bannually\b|\byearly\b|\bevery year\b", 365),
    (r"\bevery (\d+) days?\b", None),
]
ACTIVITY_KEYWORDS = ["strainer", "seal", "bearing", "vibration", "alignment",
                     "lubrication", "cleaning", "clean", "calibration", "grease"]


def extract_frequencies(text):
    """Return [(days, matched_phrase)] for every frequency statement in text."""
    out, low = [], text.lower()
    for pat, days in FREQ_PATTERNS:
        for m in re.finditer(pat, low):
            out.append((int(m.group(1)) if days is None else days, m.group(0)))
    return out


def ollama_chat(prompt):
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps({"model": LLM_MODEL, "stream": False,
                         "messages": [{"role": "user", "content": prompt}],
                         "options": {"temperature": 0.2}}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["message"]["content"].strip()


def narrative(alert):
    try:
        return ollama_chat(
            "Write a 2-3 sentence maintenance alert narrative for plant staff. "
            "Use ONLY facts and numbers present in the data below — never invent "
            "costs, currency amounts, dates or schedules that are not in the data. "
            "State the avoidable downtime hours as the business impact. "
            f"Data: {json.dumps(alert, default=str)}")
    except Exception as e:
        return f"(narrative unavailable: {e})"


# --------------------------------------------------------------------------- detection
def fetch(session):
    wos = session.run("""
        MATCH (w:WorkOrder)-[:PERFORMED_ON]->(e:Equipment)
        OPTIONAL MATCH (w)-[:RESULTED_IN]->(f:FailureMode)
        RETURN e.tag AS tag, e.iso14224_class AS klass, w.wo_id AS wo_id,
               toString(w.date) AS date, w.type AS type, f.code AS code,
               w.downtime_hrs AS hrs
    """).data()
    for w in wos:
        w["date"] = datetime.strptime(w["date"], "%Y-%m-%d").date()
    return wos


def class_mean_downtime(wos, klass, code):
    hrs = [w["hrs"] for w in wos
           if w["klass"] == klass and w["code"] == code and w["hrs"]]
    return round(sum(hrs) / len(hrs), 1) if hrs else 0.0


def detect_reliability(wos):
    """overdue + chronic + sibling exposure. Pure arithmetic."""
    alerts = []
    today = TODAY()
    by_combo = defaultdict(list)
    class_of, all_tags_by_class = {}, defaultdict(set)
    for w in wos:
        class_of[w["tag"]] = w["klass"]
        all_tags_by_class[w["klass"]].add(w["tag"])
        if w["type"] == "corrective" and w["code"]:
            by_combo[(w["tag"], w["code"])].append(w)

    for (tag, code), events in sorted(by_combo.items()):
        events.sort(key=lambda w: w["date"])
        dates = [w["date"] for w in events]
        gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
        days_since = (today - dates[-1]).days
        impact = class_mean_downtime(wos, class_of[tag], code)

        if gaps:
            mtbf = sum(gaps) / len(gaps)
            risk = days_since / mtbf if mtbf else 0
            if risk >= RISK_RATIO_THRESHOLD:
                alerts.append({
                    "alert_id": f"overdue-{tag}-{code}", "kind": "overdue",
                    "severity": "high" if risk >= 1.0 else "medium", "tag": tag,
                    "code": code, "mtbf_days": round(mtbf, 1),
                    "days_since_last": days_since, "risk_ratio": round(risk, 2),
                    "n_failures": len(events), "gaps_days": gaps,
                    "avoidable_hrs": impact,
                    "evidence_wos": [w["wo_id"] for w in events],
                })
        recent = [w for w in events
                  if (today - w["date"]).days <= CHRONIC_WINDOW_DAYS]
        if len(recent) >= CHRONIC_COUNT:
            alerts.append({
                "alert_id": f"chronic-{tag}-{code}", "kind": "chronic",
                "severity": "high", "tag": tag, "code": code,
                "count_12mo": len(recent),
                "dates": [str(w["date"]) for w in recent],
                "avoidable_hrs": round(sum(w["hrs"] or 0 for w in recent), 1),
                "evidence_wos": [w["wo_id"] for w in recent],
            })
        if days_since <= SIBLING_RECENT_DAYS:
            sibs = sorted(all_tags_by_class[class_of[tag]] - {tag})
            confirmed = sorted({t for (t, c) in by_combo if c == code and t in sibs})
            unchecked = [t for t in sibs if t not in confirmed]
            if sibs:
                alerts.append({
                    "alert_id": f"siblings-{tag}-{code}", "kind": "sibling_exposure",
                    "severity": "medium", "tag": tag, "code": code,
                    "failed_on": str(dates[-1]), "siblings": sibs,
                    "confirmed_history": confirmed, "needs_check": unchecked,
                    "avoidable_hrs": class_mean_downtime(wos, class_of[tag], code),
                    "evidence_wos": [events[-1]["wo_id"]],
                })
    return alerts


def detect_divergence(session):
    """Same-topic gate, then frequency comparison (spec 8 P4)."""
    pairs = session.run("""
        MATCH (p:Procedure)-[:APPLIES_TO]->(e:Equipment)<-[:APPLIES_TO]-(t:TacitKnowledge)
        MATCH (d:Document {doc_id: p.sop_id})-[:HAS_CHUNK]->(c:Chunk)
        WITH p, e, t, c,
             vector.similarity.cosine(t.embedding, c.embedding) AS cos
        WHERE cos >= $gate
        RETURN p.sop_id AS sop, p.title AS title, e.tag AS tag,
               t.claim_id AS claim_id, t.text AS claim, t.audio_id AS audio,
               t.t_start AS t_start, t.lang AS lang,
               c.chunk_id AS chunk_id, c.text AS chunk, c.page AS page, cos
        ORDER BY cos DESC
    """, gate=DIVERGENCE_COSINE_GATE).data()

    findings = defaultdict(lambda: {"claims": {}, "chunks": {}, "tags": set(),
                                    "proc_freq_votes": defaultdict(int),
                                    "proc_phrase": {},
                                    "activity_votes": defaultdict(int)})
    for row in pairs:
        shared = [k for k in ACTIVITY_KEYWORDS
                  if k in row["claim"].lower() and k in row["chunk"].lower()]
        if not shared:
            continue                                    # same-topic gate fails
        pf = extract_frequencies(row["chunk"])
        tf = extract_frequencies(row["claim"])
        if not pf or not tf:
            continue
        p_days = {d for d, _ in pf}
        # the operator's deviating practice: frequencies the procedure does NOT
        # state. Claims usually cite the official interval while rejecting it
        # ("the book says monthly, we do it fortnightly"), so plain set
        # intersection would wrongly conclude agreement.
        deviating = sorted({d for d, _ in tf} - p_days)
        if not deviating:
            continue                                    # claim agrees with procedure
        f = findings[row["sop"]]                        # one finding per procedure
        f["sop"], f["title"] = row["sop"], row["title"]
        for k in shared:
            f["activity_votes"][k] += 1
        f["tags"].add(row["tag"])
        for d, phrase in pf:
            f["proc_freq_votes"][d] += 1
            f["proc_phrase"].setdefault(d, phrase)
        f["chunks"][row["chunk_id"]] = {"page": row["page"], "cos": round(row["cos"], 3)}
        op_days = deviating[0]                          # most frequent practice wins
        op_phrase = next(p for d, p in tf if d == op_days)
        f["claims"][row["claim_id"]] = {
            "claim_id": row["claim_id"], "text": row["claim"],
            "operators_say": op_phrase, "operators_days": op_days,
            "audio": row["audio"], "t_start": row["t_start"], "lang": row["lang"]}

    alerts = []
    for sop, f in sorted(findings.items()):
        # procedure's stated interval: majority vote across gated chunks,
        # ties broken toward the shortest interval
        votes = sorted(f["proc_freq_votes"].items(), key=lambda kv: (-kv[1], kv[0]))
        proc_days = votes[0][0]
        activity = sorted(f["activity_votes"].items(), key=lambda kv: -kv[1])[0][0]
        claims = sorted(f["claims"].values(), key=lambda c: c["claim_id"])
        tags = sorted(f["tags"])
        alerts.append({
            "alert_id": f"divergence-{sop}", "kind": "divergence",
            "severity": "high", "tag": tags[0], "tags": tags,
            "sop": sop, "sop_title": f["title"], "activity": activity,
            "procedure_says": f["proc_phrase"][proc_days],
            "procedure_days": proc_days,
            "operators_say": claims[0]["operators_say"],
            "operators_days": claims[0]["operators_days"],
            "n_independent_claims": len(claims), "claims": claims,
            "evidence_chunks": sorted(f["chunks"].keys()),
            "evidence_claims": [c["claim_id"] for c in claims],
        })
    return alerts


def write_alerts(session, alerts):
    for a in alerts:
        session.run("""
            MERGE (al:Alert {alert_id: $id})
            SET al.kind = $kind, al.severity = $severity, al.status = 'open',
                al.created_at = datetime(), al.detail = $detail,
                al.narrative = $narrative, al.avoidable_hrs = $hrs
            WITH al
            UNWIND $tags AS tag
            MATCH (e:Equipment {tag: tag})
            MERGE (al)-[:ABOUT]->(e)
        """, id=a["alert_id"], kind=a["kind"], severity=a["severity"],
             detail=json.dumps(a, default=str), narrative=a.get("narrative", ""),
             hrs=a.get("avoidable_hrs", 0.0), tags=a.get("tags", [a["tag"]]))
        for wo in a.get("evidence_wos", []):
            session.run("MATCH (al:Alert {alert_id: $id}), (w:WorkOrder {wo_id: $wo}) "
                        "MERGE (al)-[:EVIDENCED_BY]->(w)", id=a["alert_id"], wo=wo)
        for ch in a.get("evidence_chunks", []):
            session.run("MATCH (al:Alert {alert_id: $id}), (c:Chunk {chunk_id: $ch}) "
                        "MERGE (al)-[:EVIDENCED_BY]->(c)", id=a["alert_id"], ch=ch)
        for cl in a.get("evidence_claims", []):
            session.run("MATCH (al:Alert {alert_id: $id}), (t:TacitKnowledge {claim_id: $cl}) "
                        "MERGE (al)-[:EVIDENCED_BY]->(t)", id=a["alert_id"], cl=cl)


def sweep(write=True, with_narrative=True):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD),
                                  notifications_min_severity="OFF")
    with driver.session(database=NEO4J_DATABASE) as s:
        wos = fetch(s)
        alerts = detect_reliability(wos) + detect_divergence(s)
        if with_narrative:
            existing = {r["id"]: r["n"] for r in s.run(
                "MATCH (al:Alert) WHERE al.narrative <> '' "
                "RETURN al.alert_id AS id, al.narrative AS n")}
            for a in alerts:                    # LLM only for alerts it hasn't seen
                a["narrative"] = existing.get(a["alert_id"]) or narrative(
                    {k: v for k, v in a.items() if k not in ("claims",)})
        if write:
            write_alerts(s, alerts)
    driver.close()
    return alerts


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    alerts = sweep(write=not dry, with_narrative="--no-narrative" not in sys.argv)
    print(f"{len(alerts)} alerts{' (dry run)' if dry else ' written'}:\n")
    for a in alerts:
        extra = {k: v for k, v in a.items()
                 if k not in ("alert_id", "kind", "severity", "tag", "narrative",
                              "claims", "detail")}
        print(f"  [{a['severity']:6}] {a['kind']:17} {a['tag']}  {extra}")
        if a.get("narrative"):
            print(f"           {a['narrative'][:200]}")
