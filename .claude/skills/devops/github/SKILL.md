---
name: github
description: GitHub workflow (gh CLI, PRs, issues, Actions secrets, branch protection). Use when creating pull requests, issues, labels, GitHub secrets, or working with origin/gh.
---

# GitHub

**Project:** `gh` for GitHub. Free GitHub Actions minutes. Do not add paid runners or GitHub Advanced Security unless asked.

## When to use

PR/issue/release, `gh`, remote, repo secrets. What CI *runs*: `ci-cd`. Key files: `secrets`.

## Git safety

No `git config`. No force-push to `main`. No `--no-verify` unless the user asked. Do not commit `.env`.

## Branches

`main` protected. Features: `feat/…`, `fix/…`, `chore/…`.

## PRs (only if the user asked)

1. `git status`, diff, log vs `main`, upstream tracking.
2. Push `-u` if needed.
3. `gh pr create`:

```markdown
## Summary
- Why (1–3 bullets)

## Test plan
- [ ] How to verify
```

`Fixes #n` only when true. Do not self-merge unless asked.

## Secrets

Actions **secrets** for LLM/Supabase service role/deploy SSH. **Variables** for non-secret names (region, bucket). Never put secrets in workflow YAML or PR bodies.

## Hygiene

Pin third-party Actions by SHA when adding workflows. Dependabot later if dependency noise grows.

## Do not

Create/visibility-change the GitHub repo unless asked. Paste PATs or `GITHUB_TOKEN`.
---
