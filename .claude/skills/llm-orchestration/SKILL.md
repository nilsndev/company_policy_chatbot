---
name: llm-orchestration
description: LLM calling layer (providers, streaming, tools, structured output, retries, model routing). Use when adding chat completions, tool loops, JSON mode, fallbacks, or swapping OpenAI/Anthropic/local models.
---

# LLM Orchestration

## Abstraction

- One `LLMClient` interface: `stream_chat`, `complete`, `complete_json`.
- Provider SDKs live behind it. Routes and React never import OpenAI/Anthropic directly.
- Model ids and temperature live in config. Log `model`, `latency_ms`, `prompt_tokens`, `completion_tokens`.

## Streaming

- Default path is streaming. Buffering the full answer is only for judges/evals/tools that need JSON.
- Propagate cancel from the HTTP client to the provider request.

## Tools / agents

- Tools are typed JSON schemas. Validate arguments before executing.
- Side-effect tools (email, delete, pay) require explicit user confirmation unless the user already designed auto-run.
- Bound the tool loop (e.g. max 8 hops). On limit, return a partial + error.

## Structured output

- Prefer provider JSON schema / tool-forced output over “please return JSON”.
- Validate with Pydantic. On failure: one repair pass, then error.

## Reliability

- Timeouts on every call. Retry with backoff only on 429/5xx and network.
- Fallback chain: primary model → cheaper/smarter backup → cached/canned error to user.
- Never retry non-idempotent tool executions.

## Routing

- Simple chat: small/fast model.
- RAG synthesis: mid model.
- Hard reasoning / judges: stronger model.
- Embeddings: dedicated embed model, never the chat model.

See also: `prompt-engineering`, `agent-graphs`, `cost-governance`.
---
