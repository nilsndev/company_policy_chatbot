---
name: background-jobs
description: Async workers for ingest, embed, reindex, and summaries. Use when adding queues, Celery/Arq/RQ, retries, or moving work off the request thread.
---

# Background Jobs

## What belongs on a worker

- Parse, chunk, embed, reindex
- Conversation summarization
- Eval batch runs
- Outbound webhooks

Chat **token generation** stays on the API process (SSE). Do not queue the user’s live stream.

## Queue

- Redis-backed (Arq, RQ, or Celery). One queue `ingest`, one `default`.
- Job payload: ids only (`document_id`), not raw file bytes.
- At-least-once: handlers are idempotent.

## Retries

- Exponential backoff. Give up to DLQ after N tries.
- Do not retry on validation errors (bad MIME, too large).

## Observability

- Job id in logs. Status column for the UI.
- Metrics: queue depth, time-to-ready, fail rate.

## Do not

- Start a daemon thread inside FastAPI as the production ingest system.
- Pass the service-role key as a job argument (workers read env).
---
