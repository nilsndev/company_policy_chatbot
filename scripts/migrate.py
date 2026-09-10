"""Apply pending SQL migrations in supabase/migrations/ to the Supabase Cloud dev project.

No Supabase CLI/Docker locally (see `local-dev` skill) — this connects directly with
DATABASE_URL from .env and tracks applied filenames in a schema_migrations table.

Usage: python scripts/migrate.py
"""

import asyncio
import sys
from pathlib import Path

import psycopg
import truststore

truststore.inject_into_ssl()

if sys.platform == "win32":
    # psycopg's async driver can't run on Windows' default ProactorEventLoop.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "supabase" / "migrations"


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set in .env")

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        await conn.execute(
            "create table if not exists schema_migrations ("
            "filename text primary key, applied_at timestamptz not null default now())"
        )
        async with conn.cursor() as cur:
            await cur.execute("select filename from schema_migrations")
            applied = {row[0] for row in await cur.fetchall()}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                print(f"skip  {path.name} (already applied)")
                continue
            print(f"apply {path.name}")
            await conn.execute(path.read_text())
            await conn.execute(
                "insert into schema_migrations (filename) values (%s)", (path.name,)
            )
        await conn.commit()


if __name__ == "__main__":
    asyncio.run(main())
