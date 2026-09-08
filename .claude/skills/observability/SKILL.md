---
name: observability
description: Tracing, logging, and LLM telemetry (OpenTelemetry, Langfuse-style traces, token usage, PII). Use when adding logs, traces, dashboards, debugging production chat, or cost metrics.
---

# Observability

## What to record

Every chat request:

- `request_id`, `user_id`, `conversation_id`
- retrieval: query, filters, chunk ids, scores (not full chunk text in cheap logs)
- LLM: model, prompt version, tokens in/out, latency, finish reason
- errors: type, provider status, no stack traces to clients

Prefer a trace tree: `http.chat` → `retrieve` → `rerank` → `llm.stream`.

## PII

- Redact emails, phone numbers, and pasted secrets before sending to third-party trace tools.
- Default: store spans; sample raw prompts in production (e.g. 1–5%) unless the user wants 100% in staging.

## Logs

- Structured JSON logs. `INFO` for request complete, `WARNING` for retries, `ERROR` for failures.
- Correlate with `request_id` in API, worker, and frontend error reports.

## Alerts

- Spike in 5xx, LLM 429, retrieval empty-rate, p95 latency, cost per 1k requests.

## Do not

- Log full `Authorization` headers or service-role keys.
- Print entire retrieved corpora at INFO.
---
