# own_chatbot — MHN Policy Assistant

Personal full-stack **RAG + graph chatbot** for a fake company, **Meridian Health Network (MHN)**: employees sign in, ask grounded questions about company policy, and get cited answers scoped to what their role/department is allowed to see. See [`PRD.md`](PRD.md) for the company profile, personas, and requirements, and [`PROGRESS.md`](PROGRESS.md) for milestone status.

This file is **global** project context. Domain workflows live in [`.claude/skills/`](.claude/skills/README.md). Do not duplicate skill content here.

## Stack

| Layer | Choice |
| --- | --- |
| API | FastAPI (Python), SSE for chat tokens |
| UI | React + TypeScript |
| Relational / auth / files / vectors | **Supabase** — hosted free-tier cloud project, dev included (not the local CLI) |
| Graph | **Neo4j Aura Free** — hosted free-tier cloud instance, dev included (not local/container Neo4j) — policy relationships (GraphRAG) *and* the department/role RBAC graph — see skill `graph` |
| Jobs | Worker as a second native process on the same host as the API (Redis optional later) |
| LLM | **Ollama** (native local install) behind an `LLMClient`; embeddings are a **separate**, also-local model. Swapping in a hosted provider (OpenAI/Anthropic) is a possible later phase, not the default |
| Local | Native processes only — Python venv (`uvicorn`) + npm/Vite + local Ollama + `.env` (never committed). **No Docker/container virtualization for local dev** — unsupported on this machine's current network, see skill `local-dev` |
| Cloud | **AWS free tier only**, later phase — see skill `aws`. Containers there (ECS/Fargate) are a separate later decision, not blocked by the local constraint above |
| Git | GitHub Actions on the free plan (CI runners are hosted, unaffected by the local Docker constraint) |

Two data stores are approved for this project: **Supabase/pgvector** (relational, auth, files, vectors) and **Neo4j** (graph). This was an explicit user decision — do not treat it as scope creep. Do not add a *third* database, vector store, queue, or cloud provider until the user asks. Do not assume ECS, ALB, RDS, or ElastiCache.

## Layout (target)

```
app/           # FastAPI: api, core, models, services, workers
(frontend)     # React app when added
.claude/       # commands + nested skills
```

Today the repo is early (`main.py` placeholder). New code should follow the target layout and the matching skill.

## Product loops

Ship features that complete a loop, not a single layer:

1. **Signup → chat** — Auth, profile (dept + role), streamed reply, history reload.
2. **Upload → ask** — Job `queued|ready|failed`, retrieval scoped to that user's department/role via the Neo4j RBAC graph, real citations.
3. **Multi-turn** — History/summary budget, Stop cancels the provider stream, new thread does not leak.
4. **Isolation** — Employee B never sees a policy A's department can't see (Supabase RLS + server checks + Neo4j graph scoping, not just app-layer filtering).
5. **Ship** — lint/tests on PR; deploy only free-tier topology; `/health` and `/ready`.
6. **Improve RAG** — golden-set baseline, one change (vector-only vs vector+graph), eval delta, then merge.

## Agent rules

- Read the **domain skill** before editing that layer. Catalog: `.claude/skills/README.md`.
- Never read or commit `.env` or keys (`secrets` skill + Cursor rule).
- Do not claim RAG quality improved without an eval (or an explicit waiver).
- Prefer extending an existing skill over adding a tiny new one.

## Commands

- `/onboard` — map the repo
- `/build` — execute a plan
---
