"""Plant Brain — FastAPI backend + responsive web UI (spec 5, 8, 9).

Run:  py app.py          (serves http://localhost:8000)

Endpoints:
  POST /api/ask            {question} -> cited answer, confidence, citations, timing
  GET  /api/alerts         open alerts with evidence chains (Watch agent output)
  POST /api/watch/run      trigger a Watch sweep now
  GET  /api/stats          graph counts + entity-resolution panel data
  GET  /api/doc/{doc_id}   procedure PDF (citation click-through, #page= anchor)
  GET  /api/audio/{name}   voice clip (seek-to-timestamp playback)

The Watch agent runs on an APScheduler timer (spec 5); narratives are only
generated for alerts that don't have one yet, so sweeps stay cheap.
"""

import json
import sys
from pathlib import Path

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "pipeline"))
from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,  # noqa: E402
                    CORPUS)
from neo4j import GraphDatabase                                             # noqa: E402
import ask as ask_mod                                                       # noqa: E402
import watch as watch_mod                                                   # noqa: E402

app = FastAPI(title="Plant Brain")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD),
                              notifications_min_severity="OFF")


class Question(BaseModel):
    question: str


@app.post("/api/ask")
def api_ask(q: Question):
    return ask_mod.ask(q.question)


@app.get("/api/alerts")
def api_alerts():
    with driver.session(database=NEO4J_DATABASE) as s:
        rows = s.run("""
            MATCH (al:Alert)
            OPTIONAL MATCH (al)-[:ABOUT]->(e:Equipment)
            RETURN al.alert_id AS alert_id, al.kind AS kind, al.severity AS severity,
                   al.narrative AS narrative, al.detail AS detail,
                   al.avoidable_hrs AS avoidable_hrs,
                   toString(al.created_at) AS created_at,
                   collect(e.tag) AS tags
            ORDER BY CASE al.severity WHEN 'high' THEN 0 ELSE 1 END, al.kind
        """).data()
    for r in rows:
        r["detail"] = json.loads(r["detail"]) if r["detail"] else {}
    return rows


@app.post("/api/watch/run")
def api_watch_run():
    alerts = watch_mod.sweep(write=True, with_narrative=True)
    return {"alerts_found": len(alerts)}


@app.get("/api/stats")
def api_stats():
    with driver.session(database=NEO4J_DATABASE) as s:
        counts = {r["label"]: r["n"] for r in s.run(
            "MATCH (n) WITH labels(n)[0] AS label, count(*) AS n RETURN label, n")}
        resolution = s.run("""
            MATCH (e:Equipment) WHERE size(e.aliases) > 1
            RETURN e.tag AS tag, e.aliases AS aliases ORDER BY size(e.aliases) DESC
        """).data()
        langs = [r["l"] for r in s.run(
            "MATCH (t:TacitKnowledge) RETURN DISTINCT t.lang AS l")]
    return {"counts": counts, "entity_resolution": resolution,
            "tacit_languages": langs}


@app.get("/api/doc/{doc_id}")
def api_doc(doc_id: str):
    path = CORPUS / "procedures" / f"{doc_id}.pdf"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/audio/{name}")
def api_audio(name: str):
    path = CORPUS / "audio" / Path(name).name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")


scheduler = BackgroundScheduler()
scheduler.add_job(lambda: watch_mod.sweep(write=True, with_narrative=True),
                  "interval", minutes=30, id="watch")


@app.on_event("startup")
def startup():
    scheduler.start()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
