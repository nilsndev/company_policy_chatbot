---
name: docker
description: Docker images and Compose for the chatbot (API, worker, frontend, local deps). Use when writing Dockerfiles, compose files, local containers, or image build issues.
---

# Docker

## Images

- Multi-stage builds. Final image: non-root user, only runtime deps.
- API: Python slim. Frontend: nginx or Node serve from a builder stage.
- `PYTHONUNBUFFERED=1`. Pin base image digests when going to prod.
- Copy dependency manifests first; copy source after install.

## Compose (local)

Typical services: `api`, `worker`, `web`, `db` (or Supabase local), `redis`.

- Bind-mount source only in development.
- Healthchecks on api and db. `depends_on: condition: service_healthy`.
- Secrets via env file, not `environment:` hardcoded keys. `.env` is gitignored.

## Networking

- Frontend talks to API through Compose network or a Vite proxy. Do not hardcode `localhost` inside containers (use service names).

## Do not

- Bake `.env`, API keys, or `service_role` into layers.
- Run `latest` tags in production compose.
- Use one container for API + worker + ingest in production.
---
