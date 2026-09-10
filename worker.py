"""Local dev entrypoint for the ingest worker: `python worker.py`.

Same Windows event-loop-policy fix as `run.py` (psycopg's async driver can't run
on the default ProactorEventLoop) and the same TLS-interception fix as
`app/main.py`/`scripts/migrate.py` (see PROGRESS.md M0 notes).
"""

import asyncio
import logging
import sys

import truststore

truststore.inject_into_ssl()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import get_settings  # noqa: E402
from app.services.db import create_pool  # noqa: E402
from app.workers.ingest import run_worker  # noqa: E402


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    pool = create_pool(settings)
    await pool.open()
    try:
        await run_worker(pool, settings)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
