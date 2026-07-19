"""P2 Voice Capture: audio in any language -> :TacitKnowledge nodes (spec 8 P2).

Run:  py pipeline/voice_capture.py            (clips in corpus/audio/)
      py pipeline/voice_capture.py --preload  (just download the whisper model)

Pipeline per clip:
  1. faster-whisper large-v3, CPU int8, task="translate": any language -> English
     in one pass, keeping per-segment timestamps + detected source language.
  2. Tag recovery: NEVER trust ASR for equipment tags (spec 8/14). The transcript
     goes through resolve.normalise_spoken ("pee one oh one a" -> "P101a") and the
     tag regex; the LLM is given only these verified candidates.
  3. LLM structuring: rambling speech -> typed claims (equipment, condition,
     action, claim_type, t_start back into the audio).
  4. TacitKnowledge nodes with embeddings + APPLIES_TO; raw spoken spellings
     (e.g. "p-101a") land on Equipment.aliases.

:TacitKnowledge stays a separate label from :Procedure — one person's unverified
practice vs approved policy (spec 7, the one schema rule that must not be broken).
"""

import json
import sys
import urllib.request
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).parent))
from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
                    CORPUS, OLLAMA_BASE_URL, LLM_MODEL, EMBED_MODEL, EMBED_DIM)
from resolve import normalise_spoken, find_mentions_raw

AUDIO_DIR = CORPUS / "audio"
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
WHISPER_MODEL = "large-v3"          # do NOT downsize (spec 4): Indian-language accuracy


def ollama(path, payload):
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def embed(texts):
    out = ollama("/api/embed", {"model": EMBED_MODEL, "input": texts})
    vecs = out["embeddings"]
    assert all(len(v) == EMBED_DIM for v in vecs), "embedding dimension drift!"
    return vecs


def load_model():
    from faster_whisper import WhisperModel
    print(f"loading faster-whisper {WHISPER_MODEL} (CPU, int8)...")
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe(model, path: Path):
    segments, info = model.transcribe(str(path), task="translate", beam_size=5)
    segs = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()}
            for s in segments]
    return segs, info.language, round(info.language_probability, 3)


def structure_claims(audio_id, segs, candidates):
    """LLM turns the translated transcript into typed claims (closed tag list)."""
    transcript = "\n".join(f"[{s['start']}-{s['end']}] {s['text']}" for s in segs)
    prompt = (
        "Below is the English translation of a retiring plant operator's spoken "
        "knowledge, with [start-end] second timestamps.\n\n"
        f"{transcript}\n\n"
        f"Verified equipment tags mentioned (use ONLY these, never invent tags): "
        f"{candidates or ['(none)']}\n\n"
        "Extract every distinct piece of operational knowledge as a claim. Reply "
        "with JSON only:\n"
        '{"claims": [{"equipment": ["TAG"...], "condition": "situation/symptom", '
        '"action": "what the operator does/recommends", '
        '"claim_type": "practice|warning|diagnostic", '
        '"claim_text": "one-sentence self-contained statement of the knowledge", '
        '"t_start": <seconds>, "t_end": <seconds>}]}\n'
        "Use the timestamp of the segment(s) the claim came from. A claim about "
        "frequency of a maintenance task (e.g. cleaning intervals) MUST be its own claim."
    )
    out = ollama("/api/chat", {
        "model": LLM_MODEL, "stream": False, "format": "json",
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0},
    })
    claims = json.loads(out["message"]["content"]).get("claims", [])
    ok = []
    for c in claims:
        c["equipment"] = [t for t in c.get("equipment", []) if t in candidates]
        if c.get("claim_text"):
            ok.append(c)
    return ok


def main():
    if "--preload" in sys.argv:
        load_model()
        print("whisper model cached.")
        return

    clips = sorted(p for p in AUDIO_DIR.iterdir()
                   if p.suffix.lower() in AUDIO_EXTS) if AUDIO_DIR.exists() else []
    if not clips:
        print(f"no audio clips found in {AUDIO_DIR} — record per "
              "docs/voice_recording_scripts.md and re-run.")
        return

    model = load_model()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as s:
        tag_keys = {r["key"]: r["tag"] for r in s.run(
            "MATCH (e:Equipment) RETURN replace(e.tag,'-','') AS key, e.tag AS tag")}
        for clip in clips:
            audio_id = clip.stem
            segs, lang, lang_p = transcribe(model, clip)
            full = " ".join(x["text"] for x in segs)
            print(f"\n{clip.name}: detected language={lang} (p={lang_p})")
            print(f"  translation: {full[:180]}...")

            # tag recovery over normalised transcript; keep raw spoken spellings
            norm = normalise_spoken(full)
            found = find_mentions_raw(norm) + find_mentions_raw(full)
            candidates, aliases = [], []
            for key, raw in found:
                if key in tag_keys:
                    tag = tag_keys[key]
                    if tag not in candidates:
                        candidates.append(tag)
                    if raw != tag:
                        aliases.append((tag, raw))
            print(f"  tags recovered: {candidates}")

            claims = structure_claims(audio_id, segs, candidates)
            if not claims:
                print("  [warn] no claims extracted")
                continue
            vecs = embed([c["claim_text"] for c in claims])
            payload = [{
                "claim_id": f"{audio_id}-k{i:02d}", "text": c["claim_text"],
                "lang": lang, "speaker_role": "retiring operator",
                "audio_id": clip.name, "claim_type": c.get("claim_type", "practice"),
                "condition": c.get("condition", ""), "action": c.get("action", ""),
                "t_start": float(c.get("t_start", 0)), "t_end": float(c.get("t_end", 0)),
                "embedding": v, "equipment": c["equipment"],
            } for i, (c, v) in enumerate(zip(claims, vecs), 1)]
            s.run("""
                UNWIND $claims AS c
                MERGE (t:TacitKnowledge {claim_id: c.claim_id})
                SET t.text = c.text, t.lang = c.lang, t.speaker_role = c.speaker_role,
                    t.audio_id = c.audio_id, t.claim_type = c.claim_type,
                    t.condition = c.condition, t.action = c.action,
                    t.t_start = c.t_start, t.t_end = c.t_end, t.embedding = c.embedding
                WITH t, c UNWIND c.equipment AS tag
                MATCH (e:Equipment {tag: tag})
                MERGE (t)-[:APPLIES_TO]->(e)
            """, claims=payload)
            for tag, raw in set(aliases):
                s.run("""
                    MATCH (e:Equipment {tag: $tag})
                    SET e.aliases = CASE WHEN $raw IN e.aliases
                        THEN e.aliases ELSE e.aliases + $raw END
                """, tag=tag, raw=raw)
            for c in payload:
                print(f"  {c['claim_id']} [{c['claim_type']}] {c['text'][:100]}")
    driver.close()


if __name__ == "__main__":
    main()
