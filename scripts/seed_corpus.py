"""Seed the fake MHN policy corpus: upload raw files to Storage, upsert `policies`
rows, and enqueue an `ingestion_jobs` row for each — the worker (`worker.py`) does
the actual parse/chunk/embed work. Modeled on `scripts/migrate.py` (direct
DATABASE_URL connection, no HTTP round-trip through the API).

Rerunning is safe: `policies` upserts on `slug`, and a changed file re-enqueues a
job whose content_hash differs from what's already chunked (see `ingestion.py`) —
an unchanged file still enqueues a job, but the worker treats it as a no-op.

Usage: python scripts/seed_corpus.py
"""

import asyncio
import hashlib
import sys
from pathlib import Path

import psycopg
import truststore

truststore.inject_into_ssl()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.services import storage  # noqa: E402
from app.services.chunking import parse_document  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus" / "policies"


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set in .env")

    files = sorted(CORPUS_DIR.glob("*.md"))
    if not files:
        raise SystemExit(f"no corpus files found in {CORPUS_DIR}")

    await storage.ensure_bucket(settings)

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        slug_to_id: dict[str, str] = {}
        pending_supersedes: dict[str, str] = {}  # slug -> supersedes slug

        for path in files:
            slug = path.stem
            raw = path.read_bytes()
            meta, _ = parse_document(raw.decode("utf-8"))
            content_hash = hashlib.sha256(raw).hexdigest()
            storage_path = f"{slug}.md"

            await storage.upload_object(settings, storage_path, raw)

            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    insert into policies (slug, title, department, version, storage_path, content_hash)
                    values (%s, %s, %s, %s, %s, %s)
                    on conflict (slug) do update set
                        title = excluded.title,
                        department = excluded.department,
                        version = excluded.version,
                        storage_path = excluded.storage_path,
                        content_hash = excluded.content_hash,
                        updated_at = now()
                    returning id
                    """,
                    (slug, meta.title, meta.department, meta.version, storage_path, content_hash),
                )
                row = await cur.fetchone()
                policy_id = str(row[0])
                slug_to_id[slug] = policy_id

                await cur.execute(
                    "insert into ingestion_jobs (policy_id, status) values (%s, 'queued')",
                    (policy_id,),
                )

            if meta.supersedes:
                pending_supersedes[slug] = meta.supersedes

            print(f"queued  {slug}  (v{meta.version}{', supersedes ' + meta.supersedes if meta.supersedes else ''})")

        for slug, supersedes_slug in pending_supersedes.items():
            if supersedes_slug not in slug_to_id:
                print(f"warn    {slug}: supersedes unknown slug '{supersedes_slug}', skipping link")
                continue
            async with conn.cursor() as cur:
                await cur.execute(
                    "update policies set supersedes_policy_id = %s where id = %s",
                    (slug_to_id[supersedes_slug], slug_to_id[slug]),
                )

        await conn.commit()

    print(f"\nseeded {len(files)} policies. Run `python worker.py` to process the queue.")


if __name__ == "__main__":
    asyncio.run(main())
