---
name: supabase
description: Supabase for this app (Auth, Postgres, RLS, Storage, Realtime, pgvector). Use when adding tables, policies, SQL match functions, uploads, or anon vs service_role usage.
---

# Supabase

**Project:** All persistent data lives here (free Supabase project per env). AWS RDS/ElastiCache are out of scope on free tier (`aws`).

## When to use

Migrations, RLS, Storage, `match_chunks`, JWT mapping. HTTP auth check: `fastapi`. Client login: `react`.

## Keys

| Key | Where |
| --- | --- |
| `anon` | Browser only |
| `service_role` | FastAPI/worker only — **never** `VITE_*` |

Service role bypasses RLS: always add `user_id` filters in server queries too.

## Auth

Validate JWT on `/api`. Map `auth.uid()` to `user_id`. Create `profiles` on signup (trigger or API). Do not trust client-sent user ids.

## Tables (target)

`profiles`, `conversations`, `messages`, `documents`, `chunks`, `jobs` — every retrieval-visible row has `user_id` (or org membership later).

## RLS

Enable on all user data. Per-command policies. Storage: `storage.objects` matches document owner.

## pgvector

- `chunks.embedding vector(dim)` matching the embed model; store `embedding_model`.
- HNSW (cosine or IP **matching the model**). `WHERE user_id = :uid` in the **same** SQL as `ORDER BY embedding <=> :q LIMIT k`.
- Hybrid: `tsvector`/`pg_trgm` + vector, then rerank in the service.
- RPC `match_chunks` called from the **server**. Do not `select embedding` to the client.

## Realtime / Storage

Realtime for job rows. Chat tokens stay SSE. Uploads: signed URL via API or API proxy to Storage.

## Edge Functions

Webhooks/auth hooks only. RAG stays in FastAPI.

## Do not

- Disable RLS in prod. Mix embedding dimensions. Public buckets with user docs.
---
