"""Narrative ingestion: SOP PDFs -> Document/Procedure/Chunk nodes (spec 8 P1 path 2).

Run:  py pipeline/ingest_narrative.py     (after load_structured.py, models pulled)

Order of operations per spec:
  1. chunk on heading / numbered-step boundaries, ~600 tokens, 15% overlap
  2. regex pass finds equipment tags (resolve.py) -> MENTIONS rels + alias capture
     ("Pump 101A" in procedures becomes an alias on P-101A)
  3. only then the LLM binds relations between already-found entities against a
     closed vocabulary — here: which mentioned equipment the procedure APPLIES_TO
     (scope) versus merely cross-references. Direct Ollama JSON call, no
     LLMGraphTransformer (spec kill-criteria fallback adopted upfront since
     langchain-experimental is sunset).
  4. embeddings (nomic-embed-text, 768 dims) on every chunk + procedure
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

from neo4j import GraphDatabase
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).parent))
from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
                    CORPUS, OLLAMA_BASE_URL, LLM_MODEL, EMBED_MODEL, EMBED_DIM,
                    CHUNK_TARGET_TOKENS, CHUNK_OVERLAP)
from resolve import find_mentions_raw, display_tag

WORDS_PER_CHUNK = int(CHUNK_TARGET_TOKENS / 1.33)          # ~450 words ≈ 600 tokens
HEADING_RE = re.compile(r"^\s*(\d+)\.\s+[A-Z]")            # "4. Procedure"
STEP_RE = re.compile(r"^\s*(\d+)\.(\d+)\s+")               # "4.1  Walk down..."


def ollama(path, payload):
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def embed(texts: list[str]) -> list[list[float]]:
    out = ollama("/api/embed", {"model": EMBED_MODEL, "input": texts})
    vecs = out["embeddings"]
    assert all(len(v) == EMBED_DIM for v in vecs), "embedding dimension drift!"
    return vecs


def extract_blocks(pdf_path: Path):
    """PDF -> list of (page, text) blocks split on heading/step boundaries."""
    reader = PdfReader(str(pdf_path))
    blocks, current, cur_page = [], [], 1
    for pno, page in enumerate(reader.pages, 1):
        for line in (page.extract_text() or "").splitlines():
            if not line.strip():
                continue
            if HEADING_RE.match(line) or STEP_RE.match(line):
                if current:
                    blocks.append((cur_page, " ".join(current)))
                current, cur_page = [line.strip()], pno
            else:
                if not current:
                    cur_page = pno
                current.append(line.strip())
    if current:
        blocks.append((cur_page, " ".join(current)))
    return blocks


def make_chunks(blocks, sop_id):
    """Greedy grouping of blocks to ~target words with ~15% block overlap."""
    chunks, cur, cur_words, cur_page = [], [], 0, 1
    for page, text in blocks:
        w = len(text.split())
        if cur and cur_words + w > WORDS_PER_CHUNK:
            chunks.append({"page": cur_page, "text": "\n".join(cur)})
            keep = max(1, int(len(cur) * CHUNK_OVERLAP))     # overlap: carry tail blocks
            cur, cur_words = cur[-keep:], sum(len(t.split()) for t in cur[-keep:])
            cur_page = page
        if not cur:
            cur_page = page
        cur.append(text)
        cur_words += w
    if cur:
        chunks.append({"page": cur_page, "text": "\n".join(cur)})
    for i, c in enumerate(chunks, 1):
        c["chunk_id"] = f"{sop_id}-c{i:02d}"
    return chunks


def bind_applies_to(sop_id, title, scope_text, mentioned_tags):
    """LLM picks APPLIES_TO from a closed candidate list. Returns subset of tags."""
    if not mentioned_tags:
        return []
    prompt = (
        "You are indexing a plant maintenance procedure.\n"
        f"Procedure {sop_id}: {title}\n"
        f"Scope text:\n{scope_text}\n\n"
        f"Candidate equipment tags mentioned in the document: {mentioned_tags}\n"
        "Which of these tags does the procedure APPLY TO (in scope of the work it "
        "governs), as opposed to being merely cross-referenced? Answer with JSON: "
        '{"applies_to": ["TAG", ...]} using only tags from the candidate list.'
    )
    try:
        out = ollama("/api/chat", {
            "model": LLM_MODEL, "stream": False, "format": "json",
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": 0},
        })
        parsed = json.loads(out["message"]["content"])
        return [t for t in parsed.get("applies_to", []) if t in mentioned_tags]
    except Exception as e:                                   # LLM must not sink ingest
        print(f"  [warn] LLM binding failed for {sop_id} ({e}); "
              "falling back to all mentioned tags")
        return mentioned_tags


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    pdfs = sorted((CORPUS / "procedures").glob("SOP-*.pdf"))
    total_chunks = 0
    with driver.session(database=NEO4J_DATABASE) as s:
        tag_keys = {r["key"]: r["tag"] for r in s.run(
            "MATCH (e:Equipment) RETURN replace(replace(e.tag,'-',''),' ','') AS key, e.tag AS tag")}
        for pdf in pdfs:
            sop_id = pdf.stem
            blocks = extract_blocks(pdf)
            title_line = blocks[0][1] if blocks else sop_id
            title = re.sub(rf"^{sop_id}\s*[—-]\s*", "", title_line.split("Plant Site A")[0]).strip()
            chunks = make_chunks(blocks, sop_id)

            # regex entity pass + alias capture, per chunk
            doc_mentions = {}                                # display_tag -> raw forms
            for c in chunks:
                keys = find_mentions_raw(c["text"])
                c["mentions"] = sorted({tag_keys[k] for k, _ in keys if k in tag_keys})
                for k, raw in keys:
                    if k in tag_keys:
                        doc_mentions.setdefault(tag_keys[k], set()).add(raw)

            # embeddings in one batch per document
            vecs = embed([c["text"] for c in chunks])
            for c, v in zip(chunks, vecs):
                c["embedding"] = v

            # LLM relation binding on the scope-bearing text
            scope_text = next((c["text"] for c in chunks if "Scope" in c["text"][:400]),
                              chunks[0]["text"] if chunks else "")
            applies = bind_applies_to(sop_id, title, scope_text,
                                      sorted(doc_mentions.keys()))
            proc_vec = embed([f"{sop_id} {title}\n{scope_text}"])[0]

            s.run("""
                MERGE (d:Document {doc_id: $doc_id})
                SET d.path = $path, d.doc_type = 'procedure', d.ingested_at = datetime()
                MERGE (p:Procedure {sop_id: $sop_id})
                SET p.title = $title, p.embedding = $proc_vec
                MERGE (d)-[:DESCRIBES]->(p)
                WITH d, p
                UNWIND $chunks AS c
                MERGE (ch:Chunk {chunk_id: c.chunk_id})
                SET ch.text = c.text, ch.page = c.page, ch.doc_id = $doc_id,
                    ch.embedding = c.embedding
                MERGE (d)-[:HAS_CHUNK]->(ch)
                WITH p, ch, c
                UNWIND c.mentions AS tag
                MATCH (e:Equipment {tag: tag})
                MERGE (ch)-[:MENTIONS]->(e)
            """, doc_id=sop_id, path=str(pdf), sop_id=sop_id, title=title,
                 proc_vec=proc_vec,
                 chunks=[{k: c[k] for k in ("chunk_id", "text", "page", "embedding",
                                            "mentions")} for c in chunks])
            for tag in applies:
                s.run("MATCH (p:Procedure {sop_id: $sop_id}), (e:Equipment {tag: $tag}) "
                      "MERGE (p)-[:APPLIES_TO]->(e)", sop_id=sop_id, tag=tag)
            for tag, raws in doc_mentions.items():
                for raw in raws:
                    if raw != tag:
                        s.run("""
                            MATCH (e:Equipment {tag: $tag})
                            SET e.aliases = CASE WHEN $raw IN e.aliases
                                THEN e.aliases ELSE e.aliases + $raw END
                        """, tag=tag, raw=raw)
            total_chunks += len(chunks)
            print(f"{sop_id}: {len(chunks)} chunks, mentions {sorted(doc_mentions)}, "
                  f"applies_to {applies}")
    driver.close()
    print(f"\ningested {len(pdfs)} procedures, {total_chunks} chunks")


if __name__ == "__main__":
    main()
