---
name: graph
description: Neo4j for this app (policy relationship graph + department/role RBAC graph). Use when writing Cypher, modeling nodes/relationships, or filtering/enriching retrieval results by department, role, or policy supersedes/references links.
---

# Graph (Neo4j)

**Project:** Neo4j is the **second** approved data store (`CLAUDE.md`), used for two distinct jobs — do not conflate them in one query without thinking about which is which:

1. **RBAC graph** — who is allowed to see what (`Employee` → `Department`/`Role` → `Policy`).
2. **GraphRAG** — relationships *between* policies (`SUPERSEDES`, `REFERENCES`) that pgvector alone can't represent.

Postgres/pgvector (`supabase` skill) stays the source of truth for policy text, chunks, and embeddings. Neo4j never stores chunk text — only ids that map back to `policy_chunks.id` / `policies.id`.

## Schema

```
(:Employee {id, name})-[:MEMBER_OF]->(:Department {name})
(:Employee)-[:HAS_ROLE]->(:Role {name})
(:Policy {id, title, version})-[:APPLIES_TO]->(:Department)
(:Policy)-[:SUPERSEDES]->(:Policy)
(:Policy)-[:REFERENCES]->(:Policy)
```

`Policy.id` matches the Postgres `policies.id` — always join back through this id, never duplicate policy content into node properties beyond `title`/`version`.

## When to use

Writing/updating Cypher, the ingestion job's graph-write step, or the retrieval service's post-vector-search filter/enrich step (`PRD.md` §6.3). HTTP-layer auth (is this a valid session) stays in `fastapi`; this skill is about **what the graph says this user/policy is allowed to see or related to**, after auth already passed.

## RBAC filtering (retrieval step 3)

Given a candidate set of `policy_id`s from pgvector and the asking employee's id:

```cypher
MATCH (e:Employee {id: $employeeId})-[:MEMBER_OF]->(d:Department)
MATCH (p:Policy)-[:APPLIES_TO]->(dept)
WHERE p.id IN $candidateIds
  AND (dept = d OR dept.name = 'Company-Wide')
RETURN p.id
```

Run this **server-side only**, same as RLS — never trust a client-supplied department/role. This is the second isolation layer required by `CLAUDE.md` product loop 4; Supabase RLS is the first. Both must independently deny access — a bug in one should not be the only thing standing between a user and another department's policy.

## Supersedes / references enrichment

- If a matched policy `[:SUPERSEDES]->` another, and the *older* one is what got matched, resolve to the current version before it reaches the LLM — don't answer from a stale policy.
- Pull in directly `[:REFERENCES]`-linked policies as supplementary context, capped (e.g. depth 1, limit ~3) — don't let this balloon the context window. This is a rerank/enrichment step, not a second unbounded retrieval.

## Ingestion write path

When a policy is ingested/updated (`ingestion` skill), the graph write is a separate step from the pgvector write, same transaction boundary conceptually even though they're different databases: if one fails, surface `ingestion_jobs.status = failed` rather than leaving Postgres and Neo4j inconsistent. For v1, `SUPERSEDES`/`REFERENCES` edges are hand-authored in the seed corpus metadata, not auto-extracted from document text (`PRD.md` §9) — don't build an LLM extraction step unless the user asks for that stretch goal.

## Local dev

Neo4j runs in Docker Compose alongside Supabase local (see `local-dev`). Use the official `neo4j` image, Bolt driver from FastAPI (`neo4j` Python package), credentials from `.env` (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`) — never hardcoded.

## Do not

- Store policy chunk text or embeddings in Neo4j — ids only, Postgres is the source of truth.
- Let RBAC filtering happen only in the graph, or only in RLS — both layers, always.
- Auto-extract graph relationships from arbitrary uploaded text in v1 — hand-authored only, per `PRD.md`.
- Add a third database/graph product without the user asking.
---
