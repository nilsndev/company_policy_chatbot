---
name: testing-ai
description: Test strategy for LLM apps (unit, integration, mocked providers, Playwright, golden RAG). Use when writing pytest, frontend tests, fixtures, or CI test jobs.
---

# Testing AI Systems

## Layers

| Layer | What | LLM |
| --- | --- | --- |
| Unit | chunkers, authz filters, parsers, prompt assembly | mocked |
| API | routes, SSE framing, error codes | mocked |
| Integration | DB + RLS + ingest job | mocked embeddings optional |
| Eval | golden questions | real or recorded |
| E2E | Playwright login + send + stream | mocked API |

## Fixtures

- Fake LLM: yields predetermined tokens; records prompts for assertions.
- Fake embedder: hash-based vectors for deterministic nearest-neighbor tests.
- Isolated schema per test (transaction rollback or unique prefix).

## Assertions that matter

- Tenant A cannot retrieve tenant B chunks.
- Unanswerable golden cases refuse or abstain.
- SSE `done` fires; abort stops generation.
- Citation ids exist in the retrieved set.

## CI

- Fast mocked suite on every PR.
- Nightly eval job, non-blocking unless the user wants a gate.

## Do not

- Hit paid APIs in unit tests.
- Snapshot full model essays as the only frontend test.
---
