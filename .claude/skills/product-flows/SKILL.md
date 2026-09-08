---
name: product-flows
description: End-to-end product flows (signup, chat, ingest, eval, deploy). Use when implementing user journeys, wiring features across API/UI/DB, or checking that a change still fits the full loop.
---

# Product Flows

Implement features against these loops. If a change breaks a loop, fix it before finishing.

## 1. Signup → first chat

1. User signs up (Supabase Auth).
2. Profile row exists.
3. Empty conversation list + composer.
4. Message streams; message persisted; reload restores history.

## 2. Upload → ask the doc

1. User uploads a file.
2. Job visible (queued → ready / failed).
3. User asks a question; retrieval is scoped to their docs.
4. Answer includes citations that open the right source/span.

## 3. Multi-turn

1. Follow-up uses history + summary if long.
2. Stop cancels the stream.
3. New conversation does not leak prior context.

## 4. Isolation

1. User B cannot see User A conversations, files, or chunks.
2. Shared/org mode (if added) uses explicit membership, not “disable RLS”.

## 5. Ship

1. Tests + lint on PR.
2. Staging deploy with `/ready` green.
3. Prod promote with migrations applied first.

## 6. Improve RAG

1. Golden set baseline.
2. Change chunk/retrieve/prompt.
3. Eval delta + traces.
4. Only then ship.

When adding a feature, note which flow it belongs to and update API + UI + schema together.
---
