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

- Deterministic markdown docs in `fixtures/` (the MHN policy corpus, `PRD.md` §1) so RAG works without re-authoring content each time.
- Seed script writes to **both** the Supabase Cloud dev project (chunks/embeddings) and the Neo4j Aura dev instance (graph nodes/relationships) — keep them in sync, see `graph` skill.
- Optional: recorded embeddings for the fixture corpus, to skip re-embedding on every reset.

## Debugging

- One `DEBUG` flag for verbose retrieval logs. Off by default.
- Langfuse/OTel optional via env; app must run without them.

## Do not

- Reach for Docker/Compose for local dev — it isn't usable here. If a task seems to need it, flag that to the user instead of working around it silently.
- Require AWS credentials to chat locally.
- Commit `.env`.
---
