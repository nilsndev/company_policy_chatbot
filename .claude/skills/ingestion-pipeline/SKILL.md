---
name: ingestion-pipeline
description: Document ingest (upload, parse, chunk, embed, index, reindex jobs). Use when adding file upload, parsers, embedding jobs, crawl/load pipelines, or reindex flows.
---

# Ingestion Pipeline

## Flow

```
upload → virus/size checks → store raw (S3/Supabase Storage)
      → parse → chunk → embed → upsert chunks → mark document ready
```

- All steps are jobs with status: `queued | running | failed | ready`.
- Idempotent on `(document_id, content_hash)`. Retries must not duplicate chunks.

## Parsing

- Per MIME type: PDF, HTML, markdown, DOCX, plain text. Unknown type → fail the job with a clear error.
- Preserve page/section metadata for citations.
- Extract tables as markdown or CSV snippets, not images-only, when possible.

## Limits

- Max file size and page count in config. Reject early.
- Batch embeddings (e.g. 64–128 inputs). Respect provider TPM.

## Reindex

- On parser/chunker/embed-model change: enqueue documents, do not reembed inline in an HTTP request.
- Dual-write or version the embedding column/table so old queries keep working until swap.

## Workers

- FastAPI enqueues; a worker process runs the pipeline (see `background-jobs`).
- Dead-letter failed jobs with the exception class and document id.

## Do not

- Parse inside the upload request for large files.
- Leave `ready=true` if any chunk embed failed.
---
