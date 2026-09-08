# PRD — MHN Policy Assistant

Status: draft · Owner: solo project (portfolio piece) · Related: [`CLAUDE.md`](CLAUDE.md) (stack/rules), [`PROGRESS.md`](PROGRESS.md) (milestones)

> **This is a fictional company invented for this project.** No real organization, employee, or policy document is represented.

## 1. The fake company

**Meridian Health Network (MHN)** is a regional healthcare system (fictional) operating 6 hospitals/clinics in the Pacific Northwest, ~4,200 employees.

**Departments:** Clinical (Nursing + Physicians), IT & Security, HR, Compliance & Risk, Finance, Facilities & Operations.

**Roles per department:** `staff` → `manager` → `director`. One cross-cutting role, `compliance_officer`, can read policies across all departments.

**Policy corpus (to author as sample markdown/PDF docs during ingestion work):** ~20–30 short fictional policies across categories — Code of Conduct, Data Privacy & HIPAA-style Patient Data Handling, IT & Security (acceptable use, incident response), HR (leave, conduct, onboarding), Clinical Safety, Expense & Procurement, Facilities & Safety. Some are company-wide, some department-scoped. A few deliberately **supersede** or **reference** each other so the graph has real relationships to model, e.g. "Remote Work Policy v2" supersedes "v1", "Incident Response Policy" references "Data Privacy Policy".

## 2. Problem statement

At a company this size, policies live in scattered PDFs/wikis, go stale, and cross-reference each other in ways employees can't see. Two distinct problems compound:

1. **Findability** — plain keyword search misses paraphrased questions ("can I work from Portugal for a month?" vs. "Remote Work Policy").
2. **Scoping & relationships** — not every policy is for every employee, and policies aren't independent documents — they supersede, get superseded, and reference each other. A flat vector index can't represent either of those.

## 3. Goals

- **G1** — Grounded Q&A over the policy corpus with inline citations back to source documents/sections.
- **G2** — Answers and retrieval are scoped to the asking employee's department + role, enforced server-side, not just prompted.
- **G3** — Retrieval is relationship-aware: if a matched policy was superseded, the answer says so and cites the current version; if a related policy exists, it's surfaced.
- **G4** — Demonstrate a genuine hybrid RAG architecture (pgvector for semantic recall + Neo4j for graph traversal/rerank), with an eval showing the graph step measurably helps vs. vector-only.
- **G5** — Ship as a working local demo (native processes — venv + npm + Ollama — against hosted Supabase Cloud + Neo4j Aura Free dev instances; **no Docker**, unsupported on the dev machine's current network, see `CLAUDE.md`) with a clean enough story to walk through in an interview.

## 4. Non-goals (v1)

- No real-time policy authoring/editing UI (admins seed policies via ingestion job, not a WYSIWYG editor).
- No multi-tenant/multi-company support — one fictional company only.
- No mobile app.
- No hosted-LLM billing/cost dashboard (see `cost` skill only if it becomes relevant later).
- No production AWS deploy in v1 — local-first, cloud is a later milestone (see [`PROGRESS.md`](PROGRESS.md)).

## 5. Personas

| Persona | Department / role | Needs |
| --- | --- | --- |
| Priya, staff nurse | Clinical / `staff` | Fast answers to "can I..." questions, no interest in policy IDs, needs current version only |
| Marcus, IT admin | IT & Security / `manager` | Precise citations, wants to know when a policy changed and what superseded what |
| Dana, compliance officer | Compliance & Risk / `compliance_officer` | Cross-department visibility, needs to audit which policies reference which |
| Sam, new hire | HR / `staff` | Onboarding questions, broad company-wide policies only, hasn't been assigned department policies yet |

## 6. Functional requirements

### 6.1 Auth & profile
- Supabase Auth (email/password to start). Each user row carries `department` and `role`.
- On signup (or admin-seeded for the demo), the user is also created as an `Employee` node in Neo4j, linked to their `Department` and `Role` nodes.

### 6.2 Ingestion (policy corpus)
- Admin/job uploads policy docs (markdown or PDF) with metadata: title, department scope (or company-wide), version, supersedes (optional), references (optional).
- Pipeline: parse → chunk → embed → write chunks + embeddings to Supabase/pgvector; write/update `Policy` node + relationships in Neo4j (`APPLIES_TO`, `SUPERSEDES`, `REFERENCES`).
- Job status `queued|processing|ready|failed`, visible to the uploader.

### 6.3 Retrieval (hybrid vector + graph)
1. Embed the user's question; pgvector similarity search returns top-N candidate chunks.
2. Server resolves the asking user's `department` + `role`.
3. Neo4j query filters candidates to policies the user is allowed to see (`APPLIES_TO` traversal from their `Department`/`Role`, plus company-wide policies) and:
   - drops/flags chunks belonging to a `Policy` that `SUPERSEDES` shows it's stale, substituting the current version where possible,
   - pulls in directly `REFERENCES`-linked policies as supplementary context, capped to a small number.
4. Reranked, RBAC-filtered, relationship-enriched context goes to the LLM with a prompt that requires inline citations.
5. Response streams over SSE; citations map back to `(policy title, version, section)`.

### 6.4 Chat
- Multi-turn with a history/summary budget (see `llm`/`conversation-memory` guidance).
- Stop button cancels the in-flight provider stream cleanly.
- Starting a new thread does not leak prior thread's context.

### 6.5 Isolation / RBAC
- Enforced in at least two independent layers: Supabase RLS on chunk/policy rows, **and** the Neo4j traversal in 6.3 step 3. Neither layer alone is sufficient — this is the isolation story for the interview walkthrough.
- Verified by a test: an IT-department user's query must never surface Clinical-only policy content, and vice versa, except company-wide policies.

### 6.6 Eval
- Golden set of ~20–30 Q&A pairs per persona, covering: in-scope questions, out-of-scope questions (should be refused/scoped away), superseded-policy questions (must cite current version), cross-reference questions.
- Baseline run: vector-only retrieval. Comparison run: vector+graph. Report retrieval recall, citation accuracy, and a qualitative faithfulness check — this is the artifact for **G4**.

## 7. Data model sketch

**Neo4j graph:**
```
(:Employee {id, name})-[:MEMBER_OF]->(:Department {name})
(:Employee)-[:HAS_ROLE]->(:Role {name})
(:Policy {id, title, version})-[:APPLIES_TO]->(:Department)
(:Policy)-[:SUPERSEDES]->(:Policy)
(:Policy)-[:REFERENCES]->(:Policy)
```

**Supabase/Postgres:** `users` (mirrors Supabase Auth + department/role), `policies` (metadata mirror of the Neo4j `Policy` node, source of truth for content), `policy_chunks` (text + pgvector embedding + policy_id FK), `chat_threads`, `chat_messages`, `ingestion_jobs`.

## 8. Success metrics

- Hybrid retrieval beats vector-only on the golden set (recall and/or citation accuracy — measured, not asserted, per [`CLAUDE.md`](CLAUDE.md) agent rules).
- Zero cross-department leaks across the isolation test suite.
- End-to-end demo runs from a documented `uv`/`npm`/`ollama` startup sequence plus a seed script (no Docker), no manual DB clicking.

## 9. Risks / open questions

- Graph relationship extraction (supersedes/references) is hand-authored in the seed corpus for v1, not auto-extracted from arbitrary uploaded text — auto-extraction (LLM-based entity/relation extraction) is a stretch goal, not a v1 requirement.
- Ollama model choice/quality for both generation and embeddings is unproven for this domain — first milestone should sanity-check answer quality before building the full graph layer on top.
- **No Docker/container virtualization on the dev machine** (current network) — Supabase and Neo4j are therefore hosted free-tier cloud dev instances (Cloud project + Aura Free), not local/containerized. This is a constraint, not a preference; revisit only if the network situation changes.
