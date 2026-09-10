import asyncio
import sys
from contextlib import asynccontextmanager

import truststore

truststore.inject_into_ssl()

if sys.platform == "win32":
    # psycopg's async driver (app/services/db.py) can't run on Windows' default
    # ProactorEventLoop; uvicorn creates the loop after importing this module, so
    # setting the policy here (before that happens) takes effect for the whole app.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI  # noqa: E402

from app.api.chat import router as chat_router  # noqa: E402
from app.api.health import router as health_router  # noqa: E402
from app.api.policies import router as policies_router  # noqa: E402
from app.api.profile import router as profile_router  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.db import create_pool  # noqa: E402
from app.services.neo4j import create_driver  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = create_pool(settings)
    await pool.open()
    app.state.db_pool = pool
    app.state.neo4j_driver = create_driver(settings)
    try:
        yield
    finally:
        await pool.close()
        await app.state.neo4j_driver.close()


app = FastAPI(title="MHN Policy Assistant", lifespan=lifespan)
app.include_router(health_router)
app.include_router(profile_router)
app.include_router(chat_router)
app.include_router(policies_router)
