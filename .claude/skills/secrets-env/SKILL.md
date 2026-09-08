---
name: secrets-env
description: Protect .env and other secrets from git, logs, and agent reads. Use when touching environment variables, API keys, credentials, .env, .env.example, gitignore, or when a secret might leak into code or chat.
---

# Secrets and `.env`

## Hard rule for the agent

**Do not read, open, print, copy, or commit secret files.** If a task seems to need their contents, stop and ask the user to set values locally.

Never use Read, Grep, Glob, or Shell to inspect:

- `.env`, `.env.local`, `.env.*.local`, `.env.production`, `.env.staging`
- `credentials.json`, `serviceAccount*.json`, `*service_role*`
- `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa`, `id_ed25519`
- `secrets.yaml` / `secrets.json` with real values
- AWS/GCP/Azure credential files (`.aws/credentials`, `application_default_credentials.json`)

Allowed: **`.env.example`** (placeholders only) and docs that name variable *keys*, not values.

If a tool still returns a secret: do not repeat it in the reply. Tell the user to rotate it.

## What lives where

| File | Git | Contents |
| --- | --- | --- |
| `.env` | never | real keys, local only |
| `.env.example` | yes | same keys, dummy values |
| GitHub/AWS/Supabase secret stores | n/a | production |

Frontend public vars: only `VITE_` / `NEXT_PUBLIC_` that are *meant* to be public (anon key, URL). **Never** `service_role`, private LLM keys, or DB passwords in the client bundle.

## Agent workflow

1. Need a new setting? Add the **key** to `.env.example` with a fake value and load it via `pydantic-settings`.
2. Tell the user to copy it into `.env` themselves. Do not write `.env`.
3. Never put secrets in source, Docker layers, CI logs, commits, or skill/rule files.
4. `git add` must not include ignored secret files. If git tries to stage `.env`, unstage and fix ignore rules.

## `.env.example` style

```
OPENAI_API_KEY=sk-replace-me
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=replace-me
SUPABASE_SERVICE_ROLE_KEY=replace-me-server-only
DATABASE_URL=postgresql://user:password@localhost:5432/app
```

No live tokens. No production hostnames that are confidential.

## Runtime

- Server reads secrets from the environment. Do not `open(".env")` in app code if the platform injects env (Compose/`--env-file` is fine locally).
- Log key *names* (`missing OPENAI_API_KEY`), never values.
- Production: AWS Secrets Manager / SSM / host env. Not a committed `.env`.

## Ignore files (must exist)

Keep `.gitignore`, `.cursorignore`, and `.claudeignore` aligned so git **and** agents skip secret paths. If a secret file is already tracked, remove it from the index (`git rm --cached`) — do not `git add` the secret.

See also: `auth-security`, `local-dev`.
---
