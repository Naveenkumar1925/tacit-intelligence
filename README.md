# Plant Brain — ET AI Hackathon 2026, PS-8

Industrial knowledge platform prototype: ingests generated factory documents into a
Neo4j knowledge graph, answers questions with citations, watches equipment history for
failure patterns, and captures retiring operators' spoken knowledge in any language.

Spec: `PS8_prototype_spec.md.pdf` (in Downloads; extracted text mirrored in `docs/` if needed).

## Layout

```
datagen/            corpus generator (seeded, deterministic — never hand-edit corpus/)
  generate_corpus.py    main generator + self-verification of the 4 planted patterns
  sop_content.py        text of the 8 SOP PDFs
corpus/             generated dataset (xlsx registers + SOP PDFs + audio/)
docs/               voice_recording_scripts.md — guide for the 3 user-recorded clips
```

## Regenerate the corpus

```
py datagen/generate_corpus.py
```

Prints a pattern summary and fails loudly if any planted pattern is broken.
`DEMO_DATE` at the top of the generator drives all pattern timing — set it to the real
demo day and regenerate.

## Key locked decisions (spec §4)

- Embeddings: `nomic-embed-text`, **768 dims** — irreversible once ingested.
- LLM: qwen2.5:7b-instruct via Ollama (`OLLAMA_KEEP_ALIVE=-1`).
- ASR: faster-whisper large-v3, CPU int8, `task="translate"`.
- Neo4j 5.x single datastore (vector + full-text indexes, no separate vector DB).

## Status

- [x] Day 1: corpus generator + all 4 planted patterns (verified)
- [x] Day 1: Neo4j 5.26 + Ollama installed, schema + indexes applied
- [x] Day 1: structured load (119 WOs, LKE typo auto-corrected), narrative ingest (24 chunks, embedded)
- [x] Day 1: entity resolution — P-101A carries aliases P101-A + Pump 101A, zero duplicate nodes
- [ ] Day 1 GATE remainder: voice module coded (`pipeline/voice_capture.py`) but **blocked on user-recorded clips** (docs/voice_recording_scripts.md)
- [ ] Day 2: hybrid retrieval + graph expansion, synthesis with citations, FastAPI + chat UI, reliability queries
- [ ] Day 3: divergence UI, demo video, display features, eval, (stretch) Telegram bot
