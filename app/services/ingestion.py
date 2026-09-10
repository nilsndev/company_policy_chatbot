"""Ingest orchestration: claim a queued job, parse/chunk/embed, upsert chunks.

Idempotent on `policies.content_hash` (see `ingestion` skill) — a rerun with an
unchanged file is a no-op past the claim step; a changed file replaces all of
that policy's chunks. No retry loop for v1: a failure marks the job `failed`
with the error recorded, matching the skill's "validation errors fail, do not
retry" guidance (transient-provider retry is a stretch goal, not required for M2).
"""

from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings
from app.services import db, storage
from app.services.chunking import chunk_markdown, parse_document
from app.services.embeddings import EmbeddingClient


async def process_job(pool: AsyncConnectionPool, settings: Settings, job_id: str) -> None:
    policy_id = await db.claim_ingestion_job(pool, job_id)
    if policy_id is None:
        return  # already claimed or not queued

    try:
        source = await db.get_policy_source(pool, policy_id)

        existing_hash = await db.get_latest_chunk_hash(pool, policy_id)
        if existing_hash == source["content_hash"]:
            await db.mark_ingestion_job(pool, job_id, "ready")
            return

        raw = await storage.download_object(settings, source["storage_path"])
        _, body = parse_document(raw.decode("utf-8"))
        chunks = chunk_markdown(body)

        embedder = EmbeddingClient(settings)
        embeddings = await embedder.embed([c.content for c in chunks])

        await db.replace_policy_chunks(
            pool, policy_id, chunks, embeddings, settings.ollama_embed_model, source["content_hash"]
        )
        await db.mark_ingestion_job(pool, job_id, "ready")
    except Exception as exc:  # noqa: BLE001 - recorded on the job row, not re-raised
        await db.mark_ingestion_job(pool, job_id, "failed", f"{type(exc).__name__}: {exc}")
