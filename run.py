"""Local dev entrypoint: `python run.py` instead of `uvicorn app.main:app`.

Needed on Windows — the `uvicorn` CLI creates its event loop before importing
app.main, so the policy fix there (see app/main.py) is too late to take effect
for psycopg's async driver. Setting it here, before uvicorn.run(), works
because uvicorn.run() creates its loop after this module has already run.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
