---
name: cost-governance
description: Token budgets, caching, model routing, and spend alerts. Use when optimizing LLM cost, adding semantic cache, rate limits, or billing/usage caps.
---

# Cost Governance

## Budgets

- Per-user and per-day token caps. Soft warn in UI, hard stop with a clear error.
- Per-request max context + max output tokens in config.

## Reduce spend

1. Hybrid retrieval + rerank so the generator sees 5–8 chunks, not 40.
2. Prompt cache / repeated system prefix where the provider supports it.
3. Semantic cache for duplicate questions (short TTL, tenant-scoped).
4. Small model for classification/routing; large model for final answers only when needed.

## Rate limits

- User + IP limits on `/chat` and `/ingest`.
- Backpressure on embedding batches.

## Accounting

- Store `prompt_tokens`, `completion_tokens`, `estimated_usd` per request.
- Dashboard or weekly rollup. Alert on anomaly vs 7-day baseline.

## Do not

- Unlimited `max_tokens`.
- Cache answers across tenants.
---
