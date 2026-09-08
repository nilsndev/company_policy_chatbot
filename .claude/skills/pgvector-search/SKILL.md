---
name: pgvector-search
description: Postgres pgvector schema, indexes, and hybrid SQL for RAG. Use when writing similarity queries, HNSW/IVFFlat indexes, embedding columns, or BM25 + vector fusion.
---

# pgvector Search

## Schema

- `chunks.embedding vector(dim)` with `dim` matching the embed model.
- Store `embedding_model` on the row or table version. Do not mix dims.

## Indexes

- HNSW for interactive chat (`vector_cosine_ops` or `vector_ip_ops` matching the model).
- Build indexes concurrently in production. Analyze after bulk load.

## Query

- Always `where user_id = :uid` (or org) **in the same SQL** as `order by embedding <=> :q`.
- `limit` in SQL; do not fetch the table and sort in Python.
- Hybrid: `tsvector` / `pg_trgm` keyword query UNION/CTE with vector results, then rerank.

## RPC

- Expose retrieval as a SQL function (`match_chunks`) called from FastAPI with the user context. Avoid wide-open RPCs to the browser.

## Do not

- `select embedding` to the client.
- Sequential scan on large corpora (missing index or missing filter).
---
