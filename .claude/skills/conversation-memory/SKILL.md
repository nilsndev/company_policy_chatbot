---
name: conversation-memory
description: Short-term history, summaries, and long-term user memory for chat. Use when adding conversation history, summarization, memory extraction, or context window management.
---

# Conversation Memory

## Layers

1. **Working window**: last N turns that fit a token budget (default ~2–4k tokens of history).
2. **Rolling summary**: older turns compressed into a short synopsis stored on the conversation.
3. **Long-term memory** (optional): durable facts about the user, explicit opt-in, always user-scoped.

## Persistence

- `conversations` + `messages` in Postgres. Messages are append-only.
- Streamed assistant text is saved on `done` (and on abort as partial if desired).
- Never mix users’ histories. Conversation id is always authorized.

## Summaries

- Trigger when the window exceeds the budget, not on every message.
- Summary prompt: facts, open tasks, preferences. No chain-of-thought dump.
- Keep the last raw turns even after summarizing.

## Long-term

- Extract only stable facts (“prefers Norwegian”, “works with FastAPI”).
- Show/edit/delete in UI. Do not silently store sensitive data (health, credentials).

## Do not

- Send the entire thread forever.
- Use another user’s summary as few-shot material.
---
