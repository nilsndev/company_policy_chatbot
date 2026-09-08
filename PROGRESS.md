# PROGRESS — MHN Policy Assistant

Milestone-based tracker (no calendar dates — see [`PRD.md`](PRD.md) for requirements, [`CLAUDE.md`](CLAUDE.md) for stack rules). Update this file as work lands; don't let it drift from reality.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

## M0 — Foundations
- [ ] Supabase Cloud dev project created (free tier) — no local Supabase CLI/Docker
- [ ] Neo4j Aura Free dev instance created — no local/container Neo4j
- [ ] Ollama installed natively; chat + embedding models pulled
- [x] `.env.example` covers Supabase + Neo4j + Ollama vars
- [ ] `app/` target layout in place (api, core, models, services, workers) — Python venv, no Docker
- [ ] Health/readiness endpoints (`/health`, `/ready`)

## M1 — Signup → chat (loop 1)
- [ ] Supabase Auth wired (signup/login)
- [ ] User profile carries `department` + `role`
- [ ] Minimal chat endpoint (no RAG yet) streaming via SSE from Ollama
- [ ] React chat shell: send message, see streamed reply, reload history

## M2 — Ingestion → pgvector (loop 2, vector-only)
- [ ] Fake MHN policy corpus authored (~20–30 markdown docs, see PRD §1)
- [ ] Ingestion job: parse → chunk → embed (Ollama embedding model) → pgvector
- [ ] Job status `queued|processing|ready|failed` surfaced to caller
- [ ] Chat answers grounded in vector retrieval, with citations (no RBAC/graph filtering yet — flag this explicitly, don't ship as "done")

## M3 — Neo4j graph layer
- [ ] Graph schema live: `Employee`, `Department`, `Role`, `Policy` nodes + relationships (PRD §7)
- [ ] Seed script populates the graph from the same policy corpus/metadata used in M2
- [ ] Cypher queries for: department/role scoping, supersedes resolution, references lookup

## M4 — Hybrid retrieval + RBAC (loop 2 complete, loop 4)
- [ ] Retrieval pipeline updated to the 5-step flow in PRD §6.3 (vector candidates → graph filter/enrich → LLM)
- [ ] RLS policies in Supabase as the second isolation layer (not graph-only)
- [ ] Isolation test suite: cross-department leak checks pass
- [ ] Superseded-policy and cross-reference questions answered correctly in manual spot checks

## M5 — Multi-turn + polish (loop 3)
- [ ] History/summary budget for long threads
- [ ] Stop cancels the in-flight stream cleanly
- [ ] New thread doesn't leak prior thread context

## M6 — Eval (loop 6, ties back to PRD G4)
- [ ] Golden set authored (~20–30 Q&A pairs across personas, PRD §6.6)
- [ ] Baseline run: vector-only
- [ ] Comparison run: vector + graph
- [ ] Delta reported (recall, citation accuracy, qualitative faithfulness) — required before claiming graph retrieval "improved" anything, per [`CLAUDE.md`](CLAUDE.md) agent rules

## M7 — Ship (loop 5)
- [ ] Lint + tests gate on PR (GitHub Actions, free plan — hosted runners, unaffected by the local Docker constraint)
- [ ] README polished for portfolio use (setup, architecture diagram, demo GIF/script)
- [ ] Documented native startup sequence (venv/uvicorn + npm + ollama) + seed script is the whole local setup story — no Docker

## M8 — Cloud (later phase, not v1)
- [ ] AWS free-tier deploy plan (see `aws` skill) — only after M0–M7 are solid locally

## Notes / decisions log
- Neo4j is used for **both** GraphRAG (policy relationships) and RBAC (department/role scoping) — user decision, see [`CLAUDE.md`](CLAUDE.md) stack table.
- LLM + embeddings are local via Ollama for v1; hosted-provider swap is explicitly deferred, not assumed.
- Graph relationship extraction is hand-authored in the seed corpus, not auto-extracted — see PRD §9 for why.
- **Docker is not used for local dev** (unsupported on the current network) — Supabase and Neo4j run as hosted free-tier cloud dev instances instead (Supabase Cloud project, Neo4j Aura Free); everything else runs as native processes. See `local-dev` and `docker` skills.
