---
name: fastapi
description: FastAPI backend for this RAG app (routers, Pydantic v2, SSE chat, auth deps, job enqueue). Use when editing API routes, Python services, middleware, or backend request/response behavior.
---

# FastAPI

**Project:** Thin routers → services. Settings via `pydantic-settings`. Public API under `/api/v1`. LLM behind `LLMClient` (`llm`). DB/Auth via Supabase (`supabase`).

## When to use

New endpoints, SSE, dependencies, error mapping, enqueue ingest. UI: `react`. Jobs: `ingestion`.

## Layout

```
app/api/        # routers only
app/core/       # settings, logging, security
app/models/     # Pydantic + table models
app/services/   # RAG, LLM, ingest orchestration
app/workers/    # job handlers (same image, separate process)
```

## HTTP

- `GET /health` liveness, `GET /ready` (can reach Supabase + LLM key **present**, do not call the LLM).
- Pydantic v2 bodies. `async def` for I/O.
- Stable error `code`; no stack traces to clients.
- Inject DB/LLM/Supabase in lifespan, not import-time globals.
- Timeouts on outbound calls.

## Chat SSE

Events: `token`, `citation`, `error`, `done`. `text/event-stream`; disable proxy buffering (`X-Accel-Buffering: no`). On client disconnect, cancel the provider call. Accept `conversation_id`, `message`, optional `document_ids`. Auth + `user_id` on every retrieve/generate.

Do not queue the **live** token stream. Queue only ingest/reindex/summarize.

## Enqueue

Upload route: validate, store, insert `jobs` row, return `job_id`. Worker picks up. Do not embed in the request.

## Tests

`pytest` + `httpx.AsyncClient` + lifespan. Mock LLM and embedder (`testing`).
---
