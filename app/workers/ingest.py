"""Ingest worker: polls `ingestion_jobs` for queued rows and processes them.

Second native process on the same host as the API (CLAUDE.md stack table —
Redis-backed queueing is optional later, not required for M2). Entry point:
`python worker.py` at the repo root.
"""

import asyncio
import logging

from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings
from app.services import db
from app.services.ingestion import process_job

logger = logging.getLogger(__name__)


async def run_worker(pool: AsyncConnectionPool, settings: Settings, poll_interval: float = 3.0) -> None:
    logger.info("ingest worker started, polling every %.1fs", poll_interval)
    while True:
        job_id = await db.next_queued_ingestion_job(pool)
        if job_id is None:
            await asyncio.sleep(poll_interval)
            continue

        logger.info("processing ingestion job %s", job_id)
        await process_job(pool, settings, job_id)
