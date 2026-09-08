---
name: ci-cd
description: CI/CD for the chatbot (lint, test, eval subset, image build, deploy). Use when editing GitHub Actions, pipelines, release flow, or pre-merge checks.
---

# CI/CD

## Pipeline stages

1. Lint / typecheck (ruff, mypy or pyright, frontend tsc + eslint)
2. Unit tests
3. Integration tests (Compose or service containers)
4. Optional: small RAG eval subset (nightly or on `eval/` label)
5. Build images
6. Deploy (staging on main, prod on tag or approval)

## Rules

- PR checks must fail the merge on lint/test failure.
- Cache pip/npm. Do not commit lockfile churn unrelated to the change.
- Inject secrets from GitHub/Supabase/AWS secret stores. Never echo secrets. Repo/PR/environment setup: `github`.
- Pin Action versions by SHA when possible.

## Deploy

- Staging auto from `main`. Production: explicit promote.
- Run DB migrations as a gated job, not as a side effect of app boot in prod (boot can retry-safe light migrations only if documented).
- After deploy: hit `/health` and `/ready`.

## Do not

- Skip hooks (`--no-verify`) unless the user asked.
- Store cloud credentials in repo variables that are public.
- Run full corpus embedding in CI.
---
