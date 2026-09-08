---
name: supabase
description: Supabase Auth, Postgres, Storage, Realtime, RLS, and Edge Functions. Use when adding login, database tables, RLS policies, file uploads, realtime, or the service-role vs anon key.
---

# Supabase

## Keys

| Key | Where |
| --- | --- |
| `anon` | Browser and untrusted clients only |
| `service_role` | FastAPI/workers only. Never in Vite/React env exposed to the client |

Row Level Security is mandatory on every user-data table. Service role bypasses RLS — use it only in trusted server code with explicit tenant filters.

## Auth

- Email/OAuth via Supabase Auth. Backend validates JWT on every `/api` call.
- Map `auth.uid()` to `user_id` columns. Do not trust client-sent user ids.
- After signup: create a `profiles` row (trigger or server).

## Schema

- Enable `pgvector`. Embeddings live in the same project as app tables.
- Tables: `profiles`, `conversations`, `messages`, `documents`, `chunks`, `jobs`.
- `tenant_id` or `user_id` on every row that retrieval can see.

## RLS patterns

```sql
alter table chunks enable row level security;

create policy chunks_select_own on chunks
  for select using (auth.uid() = user_id);
```

- Separate policies per command (select/insert/update/delete).
- Storage buckets: policies on `storage.objects` matching document ownership.

## Realtime / Storage

- Realtime for job progress (`jobs` updates), not for LLM tokens (use SSE from FastAPI).
- Uploads: client requests a signed upload URL from the API, or uploads through the API which writes to Storage.

## Edge Functions

- Use for webhooks and light Auth hooks. Heavy RAG stays in FastAPI/workers.

## Do not

- Disable RLS “temporarily” in production.
- Select `*` embeddings into the client.
- Share one Supabase project’s service role across unrelated environments without separate projects.
---
