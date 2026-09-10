---
name: local-dev
description: Local development loop with no Docker (Python venv + npm, hosted Supabase Cloud dev project, Neo4j Aura Free dev instance, native Ollama, seed data, .env.example). Use when setting up the repo, running the stack, or seeding test documents. Never read `.env` — see secrets-env.
---

# Local Development

**Constraint:** Docker/container virtualization is **not usable for local dev** on this machine's current network — do not suggest `docker`, `docker compose`, `supabase start` (it shells out to Docker), or a containerized Neo4j. Everything below runs as a native process or a hosted free-tier cloud dev instance instead. See `CLAUDE.md` stack table and the `docker` skill for why this is scoped to CI/later-cloud only now.

## Bring-up

1. User copies `.env.example` → `.env` and fills keys themselves. Do not open `.env` (see `secrets-env`).
2. Cloud dev instances (both free tier, no local install needed):
   - **Supabase**: a real Supabase Cloud project used for dev (not the local CLI/Docker stack). `SUPABASE_URL`/keys point at it.
   - **Neo4j**: a **Neo4j Aura Free** instance. `NEO4J_URI` is `neo4j+s://<id>.databases.neo4j.io`, not `bolt://localhost`.
3. **Ollama** installed natively (not containerized) — `ollama pull <model>` for chat + embedding models, `OLLAMA_BASE_URL=http://localhost:11434`.
4. Python: venv + `uv`/`pip install -r requirements.txt`. Migrate/push schema to the Supabase Cloud dev project. Seed a demo user, department/role rows, and 1–2 policy docs.
5. Run API (`uvicorn`), worker, and frontend (`npm run dev`) as three separate native processes/terminals — no orchestrator required at this size.

## Conventions

- Document commands in README as plain `uv`/`npm`/`ollama` commands — no `make dev`/Compose profile, since there's no container runtime to back it.
- Frontend proxies `/api` to the API (Vite dev server config) to avoid CORS pain locally.
- Use a **separate, non-production** Supabase Cloud project and Neo4j Aura instance for dev — never point local dev at prod credentials, even though both are hosted.

## Seed

- Deterministic markdown docs in `corpus/policies/` (the MHN policy corpus, `PRD.md` §1, ~24 files with a YAML frontmatter block: title/department/version/supersedes) so RAG works without re-authoring content each time.
- `python scripts/seed_corpus.py` uploads each file to Supabase Storage and upserts `policies` + a queued `ingestion_jobs` row; `python worker.py` drains the queue (parse → chunk → embed → `policy_chunks`). Rerunning the seed script is safe — upsert on `slug`, and the worker is idempotent on `content_hash`.
- As of M2, the seed script writes to Supabase only (vector-only retrieval). Writing the same corpus into the Neo4j Aura dev instance (graph nodes/relationships for RBAC + supersedes/references) is M3 — see `graph` skill; the two are not yet kept in sync.

## Debugging

- One `DEBUG` flag for verbose retrieval logs. Off by default.
- Langfuse/OTel optional via env; app must run without them.
- This dev machine's network does TLS interception (corporate/AV SSL inspection) on outbound HTTPS/Bolt — a symptom is `SSL: CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` on a connection whose DNS/TCP work fine (seen first against Neo4j Aura). Fix: the `truststore` package + `truststore.inject_into_ssl()` called once at app startup (`app/main.py`), which delegates cert trust to the OS-native store instead of Python's bundled CA bundle — not a verification bypass. Applies to any outbound TLS call from this process, not just Neo4j.

## Do not

- Reach for Docker/Compose for local dev — it isn't usable here. If a task seems to need it, flag that to the user instead of working around it silently.
- Require AWS credentials to chat locally.
- Commit `.env`.
---
