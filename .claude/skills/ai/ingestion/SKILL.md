---
name: ingestion
description: Document ingest pipeline (upload, parse, chunk, embed, reindex, job status). Use when adding file upload, parsers, embedding batches, or background ingest/reindex work.
---

# Ingestion

**Project:** FastAPI accepts upload and **enqueues**; a worker on the same host runs the pipeline. Raw files: Supabase Storage (not a paid S3 pipeline until asked). Status for the UI: `queued | running | failed | ready`.

## When to use

New MIME type, chunk/embed job, reindex after model change, job table. Chunk policy: `rag`. SQL/RLS: `supabase`. HTTP enqueue: `fastapi`.

## Flow

```
authz + size/type checks → store raw
  → parse → chunk → embed (batched) → upsert chunks → ready
```

- Idempotent on `(document_id, content_hash)`. Retries must not duplicate chunks.
- Payload is ids, not file bytes. Worker reads Storage + env (never pass `service_role` in the job body).
- `ready` only if every chunk embedded. Validation errors (bad MIME, too large): fail, do not retry.
- Retry transient provider/network with backoff; then mark `failed` with error class + document id.

## Parse

PDF, HTML, markdown, DOCX, text. Unknown type → failed job with a clear message. Keep page/section for citations.

## Reindex

On embed-model or chunker change: enqueue documents. Do not reembed inside the upload request. Version the embedding column/model name so old rows are not mixed (see `rag` / `supabase`).

## Do not

- ECS/SQS/Lambda fan-out (not free-tier default).
- Parse large files in the request thread.
- Leave orphan embeddings after a partial failure.
---
