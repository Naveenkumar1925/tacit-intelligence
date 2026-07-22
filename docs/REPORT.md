# Plant Brain — Project Report

**ET AI Hackathon 2026 · Problem Statement 8**
Theme: Industrial Intelligence / Document Management / Knowledge Engineering / Quality

*Point-in-time status report. Generated 22 July 2026. Reflects the live state of the
system, not an earlier plan. For the reference-style document see `docs/CONTEXT.md`;
this report additionally covers the voice-capture milestone, the UI redesign, the
challenge-statement compliance audit, mobile results, and the current environment
blocker.*

---

## 0. Executive summary

Plant Brain is a **fully local** industrial knowledge-intelligence platform. It ingests
heterogeneous plant documents into a single Neo4j knowledge graph, answers questions
with citations that resolve to a page or a second of audio, watches equipment history
for failure patterns without being asked, captures retiring operators' spoken knowledge,
and maps quality findings back to the standard clause that governs them.

**Current state at a glance:**

| Dimension | Value |
|---|---|
| Working prototype | ✅ Operational, end-to-end |
| Knowledge graph | 287 nodes · 468 relationships · 16 node labels |
| Evaluation | 21/21 questions passing · 12.0 s mean latency |
| Agents | 4 of a designed 12 (Ingest, Voice, Ask, Watch) |
| Watch findings live | 8 alerts across 6 detectors — **including divergence** |
| Voice capture | ✅ Live — 1 operator clip loaded, divergence firing |
| Interface | Redesigned (industrial-amber, hero-first), mobile-responsive |
| Codebase | ~4,300 lines · 20 commits · tags `v0.1-day2-stable`, `v1.0` |
| Deployment | Single laptop, 6 GB GPU, no cloud API |

**The two differentiators** — multilingual voice capture of retiring operators, and
procedure-vs-practice divergence detection — are both now **live in the graph** for the
first time (previously the voice pipeline was code-complete but had no audio).

---

## 1. The problem (challenge context)

Professionals in asset-intensive industries spend ~**35% of working hours** searching for
information that already exists. A large Indian plant runs **7–12 disconnected document
systems**; that fragmentation drives **18–22% of unplanned downtime** because maintenance
decisions are made without complete equipment history. And the **knowledge cliff**: ~25%
of India's experienced engineers and operators retire within a decade, taking
undocumented operational knowledge with them permanently.

This is not a file-management problem. It is a safety, quality, and efficiency problem
that compounds over time.

**Judging criteria:** Innovation 25% · Business Impact 25% · Technical Excellence 20% ·
Scalability 15% · User Experience 15%.

---

## 2. Challenge-statement compliance audit

Verified against the actual code, not from memory.

### 2.1 The five "what you may build" areas

| Area | Coverage | What exists / what does not |
|---|---|---|
| **Universal Document Ingestion & Knowledge Graph** | 🟡 Strong, partial | Ingests **PDFs, spreadsheets, clause documents, and audio** into one graph with entity extraction and automatic relationship linking, updating as new records arrive. **Not built:** P&ID / drawing parsing, OCR of scanned forms, email archives — all three deliberately cut (see §9). |
| **Expert Knowledge Copilot** | 🟢 Full | RAG + graph retrieval, source citations, **computed** confidence scores, direct links to originating page / audio-second / query. Responsive on mobile (§8). Strongest area. |
| **Maintenance Intelligence & RCA** | 🟢 Strong | Fuses work-order history, failure records, inspection findings. MTBF, overdue / chronic / sibling-exposure detection, downtime-avoided figures. RCA is *implied* (chronic flag = "same fault repeatedly, root cause never fixed") but there is **no dedicated cause-tree RCA agent**. |
| **Quality & Regulatory Compliance** | 🟡 Partial | QMS integration is real: clause-aware standard, NCR→clause mapping, capability (Cpk) and defect-trend (PPM) gap detection, compliance mapping. **Not built:** named Indian regulatory packs (Factory Act, OISD, PESO), auto-generated audit evidence packages. |
| **Lessons Learned & Failure Intelligence** | 🔴 Deferred | One of the eight documented not-yet-built agents. No incident/near-miss analysis, no external industry databases. |

**Beyond the menu:** two capabilities the challenge does not even list — **multilingual
voice capture** (directly targets the knowledge cliff) and **procedure-vs-practice
divergence**. These are the Innovation differentiators precisely because they are novel.

### 2.2 Suggested technologies

✅ RAG over heterogeneous corpora · ✅ Knowledge Graphs & ontology engineering ·
✅ QMS integration · ✅ Agentic AI (4-agent blackboard) · ❌ Computer Vision (P&ID) ·
❌ OCR & document intelligence — the last two deliberately cut.

### 2.3 Deliverables

| Required | Status |
|---|---|
| Working prototype | ✅ Operational |
| Architecture diagram | ✅ Five diagrams (`docs/architecture.html`, PNGs in `docs/img/`, mermaid in `docs/CONTEXT.md`) |
| Presentation deck | ❌ **Not yet built** — outstanding gap |
| Demo video | ⚠️ Recorded live from the demo script (§10); not a repo artifact |

### 2.4 Evaluation-focus mapping

| Evaluation focus | How addressed |
|---|---|
| Entity extraction accuracy across document types | Structured-first (no-LLM) load for clean data + regex-then-LLM for narrative; verified by hand + self-tests |
| Query answer quality on benchmark questions | 21-question eval harness, 21/21 passing |
| Knowledge graph linkage completeness | 468 relationships across 16 types; entity resolution merges 4 spellings to 1 node |
| Time-to-answer vs traditional search | Live stopwatch on every answer; 12.0 s mean, first tokens in ~2 s (streaming) |
| Compliance gap detection accuracy | Capability < 1.33 and PPM-rising detectors, mapped to clauses via NCRs |
| Cross-functional knowledge discovery | Graph traversal answers questions no single document contains; divergence fuses policy + field practice |

---

## 3. Platform and models

Hard constraint: a single laptop with a **6 GB GPU** (the plan assumed 8 GB, so
allocation was re-benchmarked).

| Model | Placement | Size | Role |
|---|---|---|---|
| `qwen2.5:7b-instruct` | 82% GPU / 18% CPU | 4.7 GB | Relation binding, transcript structuring, answer synthesis, alert narratives |
| `nomic-embed-text` | GPU | 275 MB | All embeddings, 768 dimensions — locked |
| `faster-whisper large-v3` | CPU, int8 | 1.5 GB | Speech → English (currently blocked, see §7.3) |

**Decisions on record:**
- The 7B stayed despite not fitting fully in VRAM — benchmarked at a *stable* 22–28 tok/s,
  versus a 4B alternative that fit but swung wildly (71 tok/s then 4.9). Stable beats
  fast when there is one take on stage.
- Whisper is on CPU deliberately so it never contends with the 7B for VRAM.
- Embedding dimension (768) is irreversible and was locked in the first 30 minutes.

**Stack:** Neo4j 5.26 (single datastore — native vector + Lucene full-text) · Ollama
(local inference) · FastAPI (backend + SSE streaming) · plain responsive HTML/JS (no
framework) · faster-whisper (ASR) · APScheduler (Watch timer).

---

## 4. The corpus

Every document is produced by a **seeded, deterministic, self-verifying generator** —
nothing hand-authored. The generators assert their own output on every run.

| Artefact | Count | Detail |
|---|---|---|
| Equipment register | 12 | 6 pumps sharing one class, 3 exchangers, 3 control valves |
| Work orders | 119 | 61 preventive · 40 corrective · 18 inspection, 3-year span |
| Inspection records | 6 | 2 deliberately expired |
| Procedures (SOP PDFs) | 8 | 826–910 words each |
| Quality standard | 1 | QS-001, 9 clauses, 835 words, original text |
| Quality KPIs | 72 | 3 processes × 2 metrics × 12 months |
| Non-conformance records | 6 | each linked to equipment + clause |
| Voice clips | 1 loaded | English operator clip (Tamil/Hindi planned) |

### The six planted patterns (all asserted by the generator)

| # | Pattern | Construction | Demonstrates |
|---|---|---|---|
| P1 | Overdue | P-101A, 4 seal failures at 88/84/86-day gaps, last 80 days pre-demo | MTBF ≈ 86 d, risk ratio ≈ 0.93, clears 0.8 threshold |
| P2 | Sibling exposure | Plugged-strainer on P-101A/B/C only; P-102A/B, P-103A share class but clean | One failure identifies 5 sisters, 2 with history, 3 to check |
| P3 | Chronic | P-102A, 4 vibration failures in 12 months | Same fault repeatedly, root cause unfixed |
| **P4** | **Divergence** | SOP-114 says monthly cleaning; operator says fortnightly in monsoon | **The winning finding — now live** |
| Q1 | Capability drift | PRC-301 Cpk 1.41 → 1.34 → 1.21 | Breaches 1.33 minimum; ties to CV-301A's expired calibration |
| Q2 | Defect trend | PRC-101 PPM 165 → 240 → 310 → 420 | Three consecutive rises; ties to strainer story + clause 8.5.1 |

### Injected messiness (proves entity resolution)

The same pump is written four ways: `P-101A` (work orders), `Pump 101A` (procedures),
`P101-A` (inspection), `p-101a` (voice). Date formats vary; one failure code carries a
deliberate typo the pipeline repairs.

---

## 5. Architecture

Four agents on a **blackboard**: no agent calls another; they read and write shared
graph state. This is why the eight deferred agents require zero changes to existing ones.

```
CORPUS (seeded, self-verifying)
  generate_corpus.py · generate_qms.py · voice clips
        │
INGEST & BUILD (P1) + VOICE (P2)
  structured (no LLM) · narrative (chunk→regex→LLM bind)
  clause-aware · voice (translate→tag regex→claims)
        │  → ENTITY RESOLUTION (4 spellings → 1 node)
        ▼
NEO4J — single datastore, dual retrieval mode
  VECTOR + FULL-TEXT: Chunk · Procedure · Clause · TacitKnowledge
  STRUCTURED TYPED:   Equipment · WorkOrder · QualityKPI · NCR  (never embedded)
        │
ASK (P3) + WATCH (P4)
  Ask: hybrid retrieval + graph expansion + analytics + cited synthesis
  Watch: arithmetic detection on a timer; LLM only narrates → writes :Alert back
        │
DELIVERY — FastAPI + responsive web
  Chat + citations · Alert panel · Graph explorer
```

*Rendered diagrams: `docs/img/fig1_architecture.png` … `fig5_divergence.png`.*

**The structural decision that matters most:** clean data never touches the LLM.
Spreadsheets load straight to typed nodes; only narrative documents are chunked and
embedded. This cuts the 7B's workload from ~500 chunks to ~40 (extraction ~50 min → <5
min) and removes hallucination risk from the cleanest data in the system.

---

## 6. Live knowledge graph inventory

**287 nodes · 468 relationships · 16 node labels.**

| Node label | Count | Node label | Count |
|---|---:|---|---:|
| WorkOrder | 119 | Clause | 9 |
| QualityKPI | 72 | Document | 8 |
| Chunk | 24 | Procedure | 8 |
| Equipment | 12 | FailureMode | 7 |
| Alert | 8 | NCR | 6 |
| InspectionRecord | 6 | Process | 3 |
| Area | 2 | Site | 1 |
| Standard | 1 | **TacitKnowledge** | **1** |

**Relationships:** PERFORMED_ON 119 · FOR 72 · OF 72 · RESULTED_IN 40 · APPLIES_TO 33 ·
MENTIONS 27 · HAS_CHUNK 24 · EVIDENCED_BY 19 · CONTAINS 14 · ABOUT 10 · HAS_CLAUSE 9 ·
DESCRIBES 8 · AGAINST 6 · CITES 6 · ON 6 · USES 3.

**The one schema rule that cannot be broken:** `:TacitKnowledge` and `:Procedure` are
separate labels. Spoken operator experience is unverified practice; a procedure is
approved policy. Keeping them apart is the only reason divergence detection is possible.

---

## 7. The four agents

### 7.1 P1 · Ingest & Build

Three paths: **structured** (spreadsheets → typed nodes, no LLM); **narrative** (SOP PDFs
chunk on heading/step boundaries ~600 tokens 15% overlap → regex finds entities → LLM
binds relations between known entities against a closed vocabulary); **entity resolution**
(every tag canonicalised and merged to one node with an alias list). Clause-aware
ingestion splits QS-001 on clause numbers, not token windows.

### 7.2 P2 · Voice Capture — **now live**

Audio in any language → typed `:TacitKnowledge` claims. Whisper runs `task="translate"`
(any language → English in one pass, timestamps + detected language preserved). **ASR is
never trusted for equipment tags** — the transcript is normalised for spelled-out digits
and run through the tag regex; the LLM sees only verified candidates.

**Live status:** one English operator clip (`clip_01.m4a`) is loaded and produced one
`:TacitKnowledge` claim linked to P-101A/B/C. Divergence fires from it (§7.4). See §7.3
for the ASR environment blocker and the workaround that made this possible.

### 7.3 Environment blocker — Whisper / PyAV (important)

On this machine, faster-whisper's audio decoder **PyAV fails to load** with *"An
Application Control policy has blocked this file"* — **Windows Smart App Control / WDAC**
blocking the unsigned native DLL. Confirmed OS-level (fails even with the command sandbox
disabled). Not bypassed — Windows Application Control is a security control.

**Workaround (shipped):** the voice pipeline falls back to a `<clip>.txt` **transcript
sidecar** when the ASR backend is unavailable. Everything downstream of ASR — tag
recovery, LLM claim structuring, embedding, linking, divergence — runs normally on the
operator's real words. Sidecar format: optional first line `lang: xx`, then the English
transcript. This is how `clip_01` was processed (the operator recorded the audio; only
the decoder is blocked).

**To genuinely transcribe/translate Tamil/Hindi clips**, Whisper must run — either disable
Smart App Control, or use a Python 3.12 environment where signed PyAV wheels may pass.
For additional English clips, a `.txt` sidecar is sufficient today.

### 7.4 P3 · Ask

A question → a cited answer with computed confidence. **Both retrieval legs (BM25 +
dense) always run**; an intent classifier sets the blend, never an exclusive branch.
Graph expansion (2 hops) runs inside the same Cypher round trip. Anchoring works on an
explicit tag, a class/area phrase, a process name, a clause number, **or an equipment
family** (see §7.6). Evidence order: computed analytics → clauses → graph/text by blend,
with symptom-matching history rows first. Confidence is arithmetic
(`0.5·retrieval + 0.4·citation-fraction + 0.1·overlap`); below threshold the system
abstains — *"not present in the corpus"* is the correct safety answer.

**Verified surfacing the voice claim.** Asking *"How often should the P-101A suction
strainer be cleaned, and what do operators actually recommend during monsoon?"* returns:

> "The P-101A suction strainer should be cleaned monthly according to SOP-114 [E8].
> During the monsoon, operators recommend cleaning every two weeks [E5][E6][E7]."

— citing both the procedure and the operator audio, confidence 0.877. Clicking the audio
citation plays the clip in-browser.

### 7.5 P4 · Watch

Runs on a timer; **every detection is arithmetic and Cypher — the LLM only writes the
narrative afterwards**, which is what makes findings defensible. Six detectors, **8 alerts
currently firing:**

| Detector | Rule | Firing now |
|---|---|---|
| capability | latest Cpk < 1.33 | CV-301A (PRC-301, Cpk 1.21) |
| chronic | same mode ≥ 3× in 12 months | P-101A (SER), P-102A (VIB) |
| **divergence** | same-topic gate → frequency set-difference | **P-101A/B/C — SOP-114 monthly vs operator fortnightly** |
| ppm_trend | defect rate rising 3 months | P-101A (PRC-101) |
| overdue | days-since-last ÷ MTBF ≥ 0.8 | P-101A (SER, ratio 0.91) |
| sibling_exposure | recent failure → same-class units | P-101A, P-102A (5 sisters each) |

Each alert carries an evidence chain (work orders / chunks / claims) and, where relevant,
an **avoidable-downtime figure in hours**. Quality alerts map to the governing clause.

### 7.6 Divergence detection (the differentiator) — how it was made to work

Two naive failures had to be designed around, plus one fix surfaced by the real clip:

1. **Embedding similarity alone fires on everything** on a small corpus → a **same-topic
   gate** requires shared equipment *and* a shared activity keyword before comparison.
2. **The intersection trap** — operators say *"the book says monthly, we do fortnightly"*,
   so "monthly" appears in both texts and naive set-intersection concludes agreement. The
   detector isolates the frequency the operator states that the procedure does **not**.
3. **Family-mention linkage (new, from clip_01)** — the operator said *"the P-101 pumps"*
   with no unit letter, which resolved to **zero** equipment, so the claim linked to
   nothing and divergence would silently never fire. Fixed: family mentions now expand to
   every member unit (P-101A/B/C), because operators name the family, not the unit.

**Result, live:** SOP-114 says *monthly* (30 d) · 1 operator says *every two weeks*
(14 d), across P-101A/B/C, evidenced by `clip_01.m4a` and SOP-114 chunks.

---

## 8. Interface and mobile

### 8.1 The redesign

Restyled from a developer-tool look to an **industrial-instrument** identity. Palette
grounded in plant instrumentation (safety amber against steel greys), not consumer AI.
**Two-state layout:** hero + centred prompt when idle; on the first question the hero
compacts and the conversation takes over. Demo questions are **chips** — nothing is typed
live on stage. The graph explorer is re-themed to match.

**Alert severity is deliberately not amber** (so it never collides with the accent) and is
triple-encoded: hue (red `#B3261E` high / ochre `#8A5A0B` medium), stripe weight
(5.6 px / 2.4 px), and an explicit label. Survives a bad projector.

### 8.2 Mobile compatibility — tested at 375 px, not assumed

| Surface | Result |
|---|---|
| Main app | ✅ Zero horizontal overflow, single-column panels, 42 px send button, 57 px chip tap-targets, readable 15 px body |
| Graph explorer | 🟡 Works (no overflow, touch-drag), one cosmetic legend overlap on narrow screens; pinch-zoom not wired (wheel/drag only) |

**Honest caveat:** the copilot is **responsive-adapts-to-mobile**, not **designed
mobile-first**. There is no dedicated field mode (voice-first input, oversized buttons,
offline cache). Defensible for a prototype; a candidate future improvement.

---

## 9. Deliberate scope decisions

Each cut was a full day of work carrying real risk, adding no capability not already
demonstrated through another door.

| Not built | Reason |
|---|---|
| P&ID / drawing parsing (CV) | Full day, high risk, every competing team will demo it |
| OCR / scanned documents | Adds a failure mode; corpus is generated so formats are controlled |
| Email ingestion | Another door into the same pipeline, no new capability |
| Text-to-Cypher / counting | Not in the demo script |
| Regulatory packs (Factory Act/OISD/PESO), audit evidence packages | Half a day of seeding; QMS demonstrates the mechanism |
| Lessons-learned / external databases | Deferred agent (one of the eight) |
| Mobile-first field app | Responsive web covers the story for a prototype |

Both CV and OCR appear in the suggested technologies and were cut **consciously** — see
§11 for how they fit the production design.

---

## 10. Demo script (3 minutes)

Steps 4 and 6 are what win — rehearse them hardest.

1. Run the ingest — graph counter ticks up live.
2. Entity-resolution panel — four spellings merged to one asset.
3. Ask *"P-101A keeps tripping on high vibration — has this happened before?"* — cited
   answer, stopwatch, click a citation to land on the page.
4. Ask *"How often should the P-101A suction strainer be cleaned, and what do operators
   recommend in monsoon?"* — answer fuses SOP (monthly) and operator audio (fortnightly);
   **click the audio citation → the clip plays.**
5. Alert panel — sister-pump warning, evidence chain, downtime-avoided figure.
6. Divergence card — *"SOP-114 says monthly. Operators say every two weeks during
   monsoon."*
7. Ask something outside the corpus — the system abstains.

**Record the video before polishing** — single laptop, 6 GB GPU; 30 minutes of recording
is insurance.

---

## 11. Scalability and the deferred eight

The production design is **12 agents across four tiers** (ingestion, query, intelligence,
delivery). The prototype implements 4. The remaining eight: email triage, Cypher
generation, RCA, compliance auditing, lessons-learned clustering, multi-channel
notification, drawing/P&ID parsing, OCR.

Because the architecture is a blackboard, **adding the missing eight requires changing
zero existing agents** — a new agent subscribes to the graph, writes findings back as
nodes, and every existing agent can consume them. Knowing precisely what was deferred, and
why, is engineering judgment rather than omission.

---

## 12. Measured results

A question passes only if the abstain decision is correct **and**, for answerable
questions, an expected source appears in the citations actually used.

| Suite | Passed | Mean latency |
|---|---:|---:|
| Full pipeline (21 questions) | **21 / 21** | 12.0 s |

**Retrieval ablation** (15-question maintenance suite, one leg disabled at a time):

| Configuration | Passed | Failure character |
|---|---:|---|
| Full — hybrid + graph | 15 / 15 | — |
| Dense only (no keyword) | 14 / 15 | an exact-threshold lookup |
| Keyword only (no dense) | 14 / 15 | same |
| **No graph expansion** | **11 / 15** | **every failure is an equipment-history question** |

The no-graph row is the clean architectural argument: removing graph traversal fails
*exactly* the questions whose answers share no vocabulary with the question — the class a
vector database alone cannot serve. (Honest note: dense-only and keyword-only score high
because graph anchoring still carries them; lead with the no-graph row.)

---

## 13. Engineering log — defects found by running, not reading

Recorded because *how* a system was debugged is stronger evidence than a claim it works.

1. **Truncated evidence cut the answer out of the evidence** — a 1,200-char cap sliced off
   SOP-114's monthly-interval sentence; the flagship question abstained. Fixed with full
   chunks + larger context window.
2. **Citation markers collided with the SOPs' own numbering** — `[1]` vs document section
   numbers; switched to `[E1]`.
3. **A relevant record at the bottom of a table was invisible** — the matching vibration
   row sat 7th of 7; the model overlooked it and abstained. Symptom-mode rows now sort
   first.
4. **Class-named questions anchored nothing** — *"the control valves in the process area"*
   abstained; class/area phrases now resolve to equipment sets.
5. **The confidence gate overwrote correct answers** — a noisy overlap term dragged good
   answers below threshold; weights recalibrated.
6. **The model invented a cost figure** ("$10,000/hour"); narratives now constrained to
   facts in the data.
7. **Divergence concluded agreement on the divergence** — the intersection trap; now uses
   frequency set-difference.
8. **Computed answers hedged when buried mid-prompt** — capability question refused
   despite a NOT-CAPABLE flag; computed evidence now leads and carries the process name.
9. **The system did not recognise its own refusal** — *"Not present in the corpus
   [E1][E2]."* — markers before the period broke a period-inclusive match; fixed.
10. **A planted pattern was contaminated by random data** — a stray plugged-strainer WO on
    P-102A broke the sibling split; protected combinations excluded from random generation.
11. **Family mention linked to nothing** — *"the P-101 pumps"* resolved to zero equipment,
    silently breaking divergence; family mentions now expand to member units.

**Environment findings:** GPU is 6 GB not 8; Neo4j runs as a foreground console process
(dies with its terminal); machine sleep evicts Ollama models mid-inference; Python must be
`py` not `python`; Whisper/PyAV blocked by Windows App Control (§7.3).

---

## 14. Build record

20 commits across three working days. Rollback tag `v0.1-day2-stable`; release tag `v1.0`
(current). Full snapshot in `backup_v1/` (source + git bundle + database dump) and
`backup_v1.zip` for the team — includes the portable knowledge graph.

| # | Commit | Summary |
|---:|---|---|
| 1 | `e3dcd12` | **Stable** — corpus generator, graph pipeline, Ask + Watch, web UI |
| 2 | `78b0df8` | Streaming answers, evidence fixes, eval harness |
| 3 | `babbec3` | Symptom-mode ordering, graph-first evidence |
| 4 | `df4e56b` | Class/area anchors, inspection evidence, confidence gate |
| 5 | `3fbe705` | Baseline eval + ablation |
| 6 | `a2f3522` | Post-fix eval + regression guards |
| 7 | `af54ced` | **QMS integration** — clauses, KPIs, retrieval router |
| 8 | `5da0721` | Analytics binding — process names, computed-first |
| 9 | `94540fb` | QMS alert cards, README, QMS eval questions |
| 10 | `c1e3cf4` | **Knowledge graph visualization** |
| 11 | `5b7dcfd` | VSCode launch config |
| 12 | `6e692e4` | Abstain-detection fix — eval reaches 21/21 |
| 13 | `77e190c` | Architecture document |
| 14 | `2d63220` | Full project context document |
| 15 | `d09ef18` | CONTEXT.md, Word doc, B/W diagram renderer |
| 16 | `9fb32b5` | Root copy of context document |
| 17 | `f74bec5` | Ignore Version 1 backup artifacts |
| 18 | `9d48bc7` | **Redesign UI** — hero-first, industrial amber |
| 19 | `88b53d7` | Pin preview server to port 8000 |
| 20 | `8f2b688` | **Voice capture live** — series mentions + sidecar fallback |

### Codebase map

```
datagen/     generate_corpus.py · sop_content.py · generate_qms.py · make_diagrams.py · make_docx.py
pipeline/    config · resolve · schema · load_structured · ingest_narrative · load_qms · voice_capture · ask · watch
app.py       FastAPI backend, all endpoints, APScheduler timer
static/      index.html (chat + panels) · graph.html (explorer) · eval.html (ablation chart)
scripts/     eval.py (21-question harness, 4-way ablation)
docs/        architecture.html · context.html · CONTEXT.md · REPORT.md · Plant_Brain_Context.docx · img/ · voice_recording_scripts.md
corpus/      generated dataset (never hand-edited) + audio/
backup_v1/   source + git bundle + neo4j.dump (also backup_v1.zip for the team)
```

### API endpoints

`POST /api/ask` · `POST /api/ask/stream` (SSE) · `GET /api/alerts` · `POST /api/watch/run`
· `GET /api/stats` · `GET /api/graph` (`?focus=TAG`) · `GET /api/doc/{id}` ·
`GET /api/audio/{name}`.

---

## 15. Running the system

Two services must be up before the app; the graph persists on disk, so ingestion is a
one-time operation.

**Routine startup**
1. **Neo4j** (not a service — start manually, leave the window open):
   ```
   $env:JAVA_HOME="C:\Users\krith\tools\jdk-21.0.11+10"
   & "C:\Users\krith\tools\neo4j-community-5.26.0\bin\neo4j.bat" console
   ```
   Check first: `Test-NetConnection localhost -Port 7687 -InformationLevel Quiet` (True = already up).
2. **Ollama** — usually running; else `ollama serve`.
3. **App** — `py app.py` (or F5 in VSCode). Serves http://localhost:8000.

**Full rebuild** (only after regenerating corpus / wiping DB): `generate_corpus.py` +
`generate_qms.py` → `schema.py` → `load_structured.py` → `ingest_narrative.py` →
`load_qms.py` → `voice_capture.py`. Verify with `scripts/eval.py` (`--quick` for one pass).

**Adding an English voice clip today:** drop `corpus/audio/clip_02.m4a` + a
`clip_02.txt` sidecar (English gloss; `lang:` line optional), then
`py pipeline/voice_capture.py` and `py pipeline/watch.py`.

**Neo4j Browser** (raw graph): http://localhost:7474 · user `neo4j` · password
`plantbrain`. Purpose-built explorer: http://localhost:8000/graph.

---

## 16. Current status and next steps

| Component | Status |
|---|---|
| Corpus, graph build, entity resolution | ✅ Operational |
| Ask agent (retrieval, synthesis, citations, abstention) | ✅ Operational |
| Watch agent (6 detectors, 8 alerts) | ✅ Operational |
| QMS (clauses, KPIs, compliance mapping) | ✅ Operational |
| Voice capture | ✅ Live (1 English clip; divergence firing) |
| Divergence detection | ✅ Live end-to-end |
| Web interface + graph explorer + eval harness | ✅ Operational, mobile-responsive |
| Presentation deck | ❌ Not built |
| Demo video | ⚠️ To record from §10 |
| More voice clips (multilingual) | ⚠️ Planned; Whisper blocked (§7.3) |

**Recommended remaining work (≤1 day):**
1. A second English operator clip (via sidecar) → "2 operators say" reads cleanly.
2. Generate the presentation deck (content already exists in this report + `CONTEXT.md`).
3. Record the demo video from the §10 script.
4. Optional polish: dedupe the operator citation that currently appears 3× (one claim
   attached to 3 pumps); a mobile field mode; RCA cause-tree.

**The differentiators are live.** Both novel capabilities — voice capture and
procedure-vs-practice divergence — now function end-to-end in the graph, which was the
single highest-value milestone outstanding.
