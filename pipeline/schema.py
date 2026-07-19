"""Create Neo4j constraints and indexes BEFORE any ingestion (spec section 7).

Run:  py pipeline/schema.py
Idempotent — safe to re-run. Neo4j fails quietly on missing indexes/dimension
mismatches (spec 14), so this script also prints what actually exists afterwards.
"""

import sys
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).parent))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE, EMBED_DIM

CONSTRAINTS = [
    "CREATE CONSTRAINT equipment_tag IF NOT EXISTS FOR (e:Equipment) REQUIRE e.tag IS UNIQUE",
    "CREATE CONSTRAINT document_id   IF NOT EXISTS FOR (d:Document)  REQUIRE d.doc_id IS UNIQUE",
    "CREATE CONSTRAINT workorder_id  IF NOT EXISTS FOR (w:WorkOrder) REQUIRE w.wo_id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id      IF NOT EXISTS FOR (c:Chunk)     REQUIRE c.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT failuremode_code IF NOT EXISTS FOR (f:FailureMode) REQUIRE f.code IS UNIQUE",
    "CREATE CONSTRAINT procedure_id  IF NOT EXISTS FOR (p:Procedure) REQUIRE p.sop_id IS UNIQUE",
    "CREATE CONSTRAINT tacit_id      IF NOT EXISTS FOR (t:TacitKnowledge) REQUIRE t.claim_id IS UNIQUE",
    "CREATE CONSTRAINT inspection_id IF NOT EXISTS FOR (i:InspectionRecord) REQUIRE i.record_id IS UNIQUE",
    "CREATE CONSTRAINT alert_id      IF NOT EXISTS FOR (a:Alert)     REQUIRE a.alert_id IS UNIQUE",
]

VECTOR_INDEXES = [
    ("chunk_embedding", "Chunk", "embedding"),
    ("procedure_embedding", "Procedure", "embedding"),
    ("tacit_embedding", "TacitKnowledge", "embedding"),
]

FULLTEXT = "CREATE FULLTEXT INDEX chunk_text IF NOT EXISTS FOR (c:Chunk) ON EACH [c.text]"


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as s:
        for stmt in CONSTRAINTS:
            s.run(stmt)
        for name, label, prop in VECTOR_INDEXES:
            s.run(
                f"CREATE VECTOR INDEX {name} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.{prop}) "
                "OPTIONS {indexConfig: {`vector.dimensions`: $dim, "
                "`vector.similarity_function`: 'cosine'}}",
                dim=EMBED_DIM,
            )
        s.run(FULLTEXT)

        print("=== constraints ===")
        for r in s.run("SHOW CONSTRAINTS YIELD name, type RETURN name, type"):
            print(f"  {r['name']}  ({r['type']})")
        print("=== indexes ===")
        for r in s.run("SHOW INDEXES YIELD name, type, state RETURN name, type, state"):
            print(f"  {r['name']}  {r['type']}  {r['state']}")
    driver.close()
    print("schema applied.")


if __name__ == "__main__":
    main()
