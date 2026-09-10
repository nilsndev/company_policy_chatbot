"""Seed the Neo4j RBAC + GraphRAG graph from the same policy corpus/metadata
`scripts/seed_corpus.py` uses (M3, see `graph` skill). `Policy.id` in the graph
must match the Postgres `policies.id`, so this reads the slug -> id mapping
from Postgres rather than generating its own ids — run this *after*
`scripts/seed_corpus.py` has created the `policies` rows.

Relationships written:
- (Employee)-[:MEMBER_OF]->(Department), (Employee)-[:HAS_ROLE]->(Role) are
  written on profile save (`app/api/profile.py`), not by this script.
- (Policy)-[:APPLIES_TO]->(Department), (Policy)-[:SUPERSEDES]->(Policy),
  (Policy)-[:REFERENCES]->(Policy) come from each corpus file's frontmatter
  (`department`/`supersedes`/`references`) — hand-authored, not auto-extracted
  from document text (PRD §9).

Usage: python scripts/seed_graph.py
"""

import asyncio
import sys
from pathlib import Path

import psycopg
import truststore

truststore.inject_into_ssl()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.services import neo4j as neo4j_service  # noqa: E402
from app.services.chunking import DocumentMeta, parse_document  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus" / "policies"


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set in .env")
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        raise SystemExit("NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD are not set in .env")

    files = sorted(CORPUS_DIR.glob("*.md"))
    if not files:
        raise SystemExit(f"no corpus files found in {CORPUS_DIR}")

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn, conn.cursor() as cur:
        await cur.execute("select slug, id from policies")
        slug_to_id = {slug: str(policy_id) for slug, policy_id in await cur.fetchall()}

    if not slug_to_id:
        raise SystemExit("no rows in `policies` yet — run scripts/seed_corpus.py first")

    driver = neo4j_service.create_driver(settings)
    try:
        metas: dict[str, DocumentMeta] = {}
        for path in files:
            slug = path.stem
            if slug not in slug_to_id:
                print(f"warn    {slug}: not in Postgres `policies` table yet, skipping (run seed_corpus.py first)")
                continue

            meta, _ = parse_document(path.read_text(encoding="utf-8"))
            metas[slug] = meta
            await neo4j_service.upsert_policy(driver, slug_to_id[slug], meta.title, meta.version, meta.department)
            print(f"graph   {slug}  (v{meta.version})")

        for slug, meta in metas.items():
            if meta.supersedes:
                if meta.supersedes not in slug_to_id:
                    print(f"warn    {slug}: supersedes unknown slug '{meta.supersedes}', skipping link")
                else:
                    await neo4j_service.link_supersedes(driver, slug_to_id[slug], slug_to_id[meta.supersedes])

            for ref_slug in meta.references:
                if ref_slug not in slug_to_id:
                    print(f"warn    {slug}: references unknown slug '{ref_slug}', skipping link")
                else:
                    await neo4j_service.link_references(driver, slug_to_id[slug], slug_to_id[ref_slug])

        print(f"\nseeded graph for {len(metas)} policies (Department/Role nodes are created on demand).")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
