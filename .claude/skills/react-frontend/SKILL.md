---
name: react-frontend
description: Build the React chat UI (streaming, markdown, conversation state, auth). Use when editing frontend components, chat pages, streaming tokens, layout, or client-side data fetching.
---

# React Frontend

## Stack defaults

- React + TypeScript. Functional components only.
- Server state: TanStack Query. Chat stream: local state + abort controller.
- Styling: existing project CSS approach (do not add a second UI kit).
- Verify UI in the browser after visual or interaction changes.

## Chat UX

- Message list is virtualized if history can grow long.
- User message appears immediately (optimistic). Assistant starts empty, fills via stream.
- Render assistant markdown safely (no raw HTML). Show citations as links/chips.
- States: idle, sending, streaming, error, aborted. Disable send while streaming unless Stop is shown.
- Stop button aborts fetch/EventSource and keeps partial text.

## Streaming

- Prefer SSE from `/api/v1/chat`. Parse `data:` frames; ignore comments.
- Handle `error` and `done` events. On network drop, show retry.
- Do not concatenate tokens in a way that breaks UTF-8 / surrogate pairs.

## Auth and tenancy

- Session from Supabase Auth. Attach access token on API calls.
- Redirect unauthenticated users. Never put service-role keys in the client.

## Accessibility

- Focus the composer after send. `aria-live` for new assistant text.
- Keyboard: Enter send, Shift+Enter newline.

## Do not

- Store full message history only in memory without a conversation id.
- Block the UI on embed/ingest jobs; poll or subscribe to job status instead.
---
