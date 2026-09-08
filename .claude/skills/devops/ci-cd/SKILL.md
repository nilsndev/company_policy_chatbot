---
name: ci-cd
description: CI/CD gates for this repo (lint, test, image build, free-tier deploy). Use when editing GitHub Actions workflows, PR checks, or release/promote flow.
---

# CI/CD

**Project:** GitHub Actions **free** tier. Pipeline must stay cheap: no full-corpus embed, no paid GPU, no AWS resource creation on every PR.

## When to use

Workflow YAML, required checks, deploy job. `gh`/secrets UX: `github`. What runs on the VM: `aws`. Tests: `testing`.

## Stages

1. Lint/typecheck (ruff + frontend tsc)
2. Unit tests (mocked LLM)
3. Optional: Compose integration (SQLite/Supabase local if fast)
4. Eval subset: nightly or `eval` label only (`evaluation`)
5. Build image (optional on PR; required on `main`)
6. Deploy: SSH/compose on the **single** free-tier EC2, or skip until that exists

## Rules

- PR merge blocked on lint/test failure.
- Cache pip/npm. Pin Actions by SHA.
- Secrets from GitHub secrets; never echo.
- After deploy: `/health` and `/ready`.

## Do not

- Staging+prod AWS accounts, ALB deploys, or `terraform apply` of paid services in CI.
- Skip hooks unless the user asked.
---
