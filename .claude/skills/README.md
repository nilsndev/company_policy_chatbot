# Skills catalog

Skills are **nested by domain**. Claude/Cursor should discover each leaf `SKILL.md` recursively.

```
.claude/skills/
  README.md                 ← this file (not a skill)
  ai/                       RAG, LLM, ingest, eval
  backend/                  FastAPI
  frontend/                 React
  data/                     Supabase + pgvector, Neo4j graph
  devops/                   Docker, GitHub, CI
  cloud/                    AWS free tier
  engineering/              secrets, security, test, obs, cost, local
```

## Current skills (18)

| Skill `name` | Path | Use when |
| --- | --- | --- |
| `rag` | `ai/rag` | retrieval, chunking, citations, chat memory |
| `llm` | `ai/llm` | providers, prompts, tools, graphs, routing |
| `ingestion` | `ai/ingestion` | upload, parse, embed, reindex jobs |
| `evaluation` | `ai/evaluation` | golden sets, RAG metrics |
| `fastapi` | `backend/fastapi` | API, SSE, services, enqueue jobs |
| `react` | `frontend/react` | chat UI, streaming, auth client |
| `supabase` | `data/supabase` | Auth, RLS, Storage, pgvector SQL |
| `graph` | `data/graph` | Neo4j: RBAC graph, policy supersedes/references, hybrid retrieval filtering |
| `docker` | `devops/docker` | images, Compose |
| `github` | `devops/github` | `gh`, PRs, issues, Actions secrets |
| `ci-cd` | `devops/ci-cd` | pipeline stages and gates |
| `aws` | `cloud/aws` | **free-tier** deploy only |
| `secrets` | `engineering/secrets` | `.env`, ignore files, keys |
| `security` | `engineering/security` | authz, injection, threat model |
| `observability` | `engineering/observability` | traces, tokens, PII |
| `testing` | `engineering/testing` | pytest, mocks, Playwright |
| `local-dev` | `engineering/local-dev` | run the stack locally |
| `cost` | `engineering/cost` | LLM spend + AWS free-tier caps |

Global product rules: [`CLAUDE.md`](../../CLAUDE.md) at repo root.

## How this scales to 80–100

Add a **new leaf folder** under an existing domain (`ai/rerankers/`, `backend/auth-api/`). Create a **new domain folder** only when the work does not fit (e.g. `mobile/`).

**Do not** split a tool into micro-skills (`docker-compose`, `docker-healthchecks`). Extend the parent `SKILL.md` or add `reference.md` beside it.

**Do not** add empty placeholder skills. The folders above are the taxonomy; vacant topics stay absent until there is real repo work.

## Merged from the old flat list

| Old | Now |
| --- | --- |
| `rag-engineering` + `conversation-memory` | `rag` |
| `llm-orchestration` + `prompt-engineering` + `agent-graphs` | `llm` |
| `ingestion-pipeline` + `background-jobs` | `ingestion` (+ enqueue notes in `fastapi`) |
| `rag-evaluation` | `evaluation` |
| `streaming-realtime` | `fastapi` + `react` |
| `pgvector-search` | `supabase` |
| `product-flows` | `CLAUDE.md` |
| `secrets-env` | `secrets` |
| `auth-security` | `security` |
| `aws-deployment` | `aws` (rewritten for free tier) |
| `testing-ai` | `testing` |
| `cost-governance` | `cost` |
---
