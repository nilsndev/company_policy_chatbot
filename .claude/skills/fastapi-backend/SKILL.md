---
name: fastapi-backend
description: Build and change the FastAPI backend (routers, Pydantic v2, async, SSE, deps, lifespan). Use when editing API routes, Python services, chat endpoints, auth middleware, or backend tests.
---

# FastAPI Backend

## Layout

```
app/
  api/           # routers only
  core/          # settings, logging, security
  models/        # Pydantic + SQLAlchemy/SQLModel
  services/      # RAG, LLM, ingest — no HTTP here
  workers/       # background jobs
```

- Routers stay thin: validate → call service → map errors.
- Settings via `pydantic-settings`. Never read `os.environ` ad hoc in handlers.

## API conventions

- Pydantic v2 models for all request/response bodies.
- `async def` for I/O. Use a threadpool only for blocking SDKs.
- Version public routes under `/api/v1`.
- Health: `GET /health` (liveness) and `GET /ready` (DB + vector + LLM keys present).
- Errors: HTTPException with a stable `code` field. Do not leak stack traces.

## Chat endpoint

- Prefer **SSE** (`text/event-stream`) for token streaming.
- Accept `conversation_id`, `message`, optional `document_ids`.
- Enforce auth + tenant on every chat and retrieval call.
- Support client abort: cancel the LLM request when the SSE client disconnects.

## Dependencies

```python
async def get_current_user(...) -> User: ...
async def get_db(...) -> AsyncSession: ...
```

- Inject clients (Supabase, LLM, Redis) through lifespan, not globals at import time.
- Timeouts on all outbound calls. Retry only idempotent GETs / provider-safe chat calls.

## Testing

- `pytest` + `httpx.AsyncClient` + app fixture with lifespan.
- Mock the LLM and embedding APIs. Hit a real local DB only in integration tests.

## Do not

- Run embeddings or long ingest inside a request without a job queue.
- Return the Supabase service-role key or raw provider errors to the client.
---
