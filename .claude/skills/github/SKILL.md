---
name: github
description: GitHub workflow for this repo (gh CLI, PRs, issues, Actions secrets, branch protection, environments). Use when creating pull requests, issues, labels, GitHub secrets, CODEOWNERS, Dependabot, or when the user mentions GitHub, gh, or origin.
---

# GitHub

## Tooling

Use `gh` for GitHub (issues, PRs, checks, releases). Do not scrape the website when `gh` works.

- Current PR: `gh pr view --json title,url,state,reviews,statusCheckRollup`
- Checks: `gh pr checks`
- Create PR only when the user asked. Push with `-u` if the branch has no upstream.

Never `git config`, never `--force` to `main`/`master`, never `--no-verify` unless the user asked. See `ci-cd` for pipeline contents and `secrets-env` for keys.

## Branches

- `main` is protected. Feature branches: `feat/…`, `fix/…`, `chore/…`.
- PRs target `main`. Rebase or merge locally only if the user wants; no force-push of shared branches unless they explicitly request it.
- Do not commit `.env`, keys, or `node_modules`.

## Pull requests

When the user asks to open a PR:

1. `git status`, `git diff`, `git log` vs `main`, and whether the branch tracks remote.
2. Push if needed.
3. `gh pr create` with a short title and body:

```markdown
## Summary
- Why this change exists (1–3 bullets)

## Test plan
- [ ] How to verify (API, UI, eval, or CI)
```

Link related issues with `Fixes #n` only when that is true.

## Issues and labels

- Bugs: reproduction, expected vs actual, env (not secrets).
- Features: user-facing outcome, not an implementation essay.
- Useful labels: `bug`, `enhancement`, `eval`, `infra`, `security`.

## Secrets and environments

| Place | Use |
| --- | --- |
| Repository **Actions secrets** | API keys, `SUPABASE_SERVICE_ROLE_KEY`, deploy creds |
| Repository **variables** | non-secret config (region, image name) |
| Environment `staging` / `production` | env-scoped secrets + required reviewers for prod |

Never put secrets in repo **Variables** that are readable in logs as plaintext by design, in `.github/workflows/*.yml` literals, or in PR descriptions.

## Repo hygiene

- `CODEOWNERS` for `/.github`, infra, and auth/RAG core when the team grows.
- Dependabot for Actions, pip, and npm; group noisy patch updates.
- Pin third-party Actions by commit SHA (`ci-cd`).
- Default: squash or merge commits per whatever the repo already uses; do not change merge strategy unasked.

## Do not

- Create the GitHub remote or change visibility unless the user asked.
- Approve or merge your own PR unless the user asked.
- Paste `gh` tokens, PATs, or `GITHUB_TOKEN` into chat or files.
---
