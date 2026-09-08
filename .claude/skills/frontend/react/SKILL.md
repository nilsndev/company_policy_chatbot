---
name: react
description: React chat UI (TypeScript, streaming SSE, markdown, Supabase session). Use when editing frontend components, chat pages, citations UI, or client data fetching.
---

# React

**Project:** React + TypeScript. Server state: TanStack Query. Chat stream: local state + `AbortController`. Public env only: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` (`secrets`).

## When to use

UI, chat composer, message list, job progress, login. API contract: `fastapi`. Auth session: `supabase`.

## Chat

- Optimistic user bubble; assistant fills via SSE from `/api/v1/chat`.
- Safe markdown (no raw HTML). Citations as chips linking to source/span.
- States: idle, sending, streaming, error, aborted. Stop aborts fetch and keeps partial text.
- Parse `data:` frames; handle `error` / `done`. Do not fake a stream after buffering the full answer.
- Enter send, Shift+Enter newline. `aria-live` for assistant text. Focus composer after send.

## Auth

Supabase Auth in the browser. Send access token to the API. Redirect if logged out.

## Jobs

Poll `GET /jobs/:id` or Realtime on `jobs` — not the chat SSE channel.

## Verify

After UI/behavior changes, exercise the flow in the browser (or say if browser tools are unavailable).

## Do not

- `service_role` or LLM keys in the client.
- Unbounded in-memory history without `conversation_id`.
---
