---
name: streaming-realtime
description: Token streaming and live updates (SSE, cancel, job progress). Use when implementing chat streams, EventSource, WebSockets, abort, or live ingest status.
---

# Streaming and Realtime

## Chat tokens

- **SSE from FastAPI** is the default for LLM tokens.
- Events: `token`, `citation`, `error`, `done`. One JSON object per `data:` line.
- `Content-Type: text/event-stream`, no gzip buffering, `X-Accel-Buffering: no` behind nginx.

## Cancel

- Client `AbortController` / `EventSource.close()`.
- Server: listen for disconnect; cancel provider stream; stop token billing as soon as possible.

## Job progress

- Ingest/reindex: write status rows; push via Supabase Realtime or poll `GET /jobs/:id`.
- Do not multiplex job logs onto the chat SSE channel.

## WebSockets

- Use only if you need bidirectional audio or collaborative presence. Otherwise SSE.

## Frontend

- Append tokens in requestAnimationFrame or small batches if the UI janks.
- Reconnect is for jobs, not for a mid-chat token stream (user resends).

## Do not

- Wait for the full LLM response then fake a stream in the UI.
- Leave hanging provider requests after the user hits Stop.
---
