---
name: docker
description: Docker/Compose is NOT used for local dev on this project (unsupported on the current network — see local-dev). This skill only applies to a future containerized deploy target (e.g. an EC2 box or ECS on AWS free tier), if and when that's revisited. Use when explicitly working on deploy-time containers, not local bring-up.
---

# Docker

**Constraint:** local dev does **not** use Docker — see `local-dev` for the native-process + hosted-cloud-dev-instance flow. Do not write a Dockerfile or Compose file as part of local setup work, and do not suggest `docker`/`docker compose`/`supabase start` to bring the stack up locally.

**Scope of this skill now:** only a possible future containerized **deploy** target (e.g. a single EC2 box on AWS free tier, `aws` skill), if that phase is reached and the user confirms Docker is usable in that context (it's a different environment than the local machine's current network). Until then, there is nothing to build here — don't create Dockerfiles speculatively.

## If/when a deploy-time image is actually needed

- Multi-stage, non-root, pinned runtime. `PYTHONUNBUFFERED=1`.
- Copy lockfiles before source. No `.env` or keys in layers.
- One API image, worker as the same image with a different command. Do not design multi-service ECS.
- `latest` never in anything called production. No baked secrets.

## Do not

- Assume Docker is available anywhere until confirmed for that specific environment — it is known **unavailable** for local dev on this machine.
- Write Dockerfiles/Compose files for local bring-up — that's `local-dev`'s job, without Docker.
---
