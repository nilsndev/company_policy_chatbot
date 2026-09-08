---
name: rag-evaluation
description: Evaluate RAG quality (golden sets, faithfulness, citation accuracy, retrieval recall). Use when adding evals, measuring RAG, comparing chunking/models, or claiming quality improvements.
---

# RAG Evaluation

## Rule

Do not claim a retrieval or prompt change improved quality unless an eval ran (or the user waived it).

## Golden set

- Store cases as JSON/YAML: `question`, `expected_doc_ids`, optional `expected_answer_points`, `forbidden_claims`.
- Cover: factual lookup, multi-hop, unanswerable, adversarial (prompt injection), tenant isolation.
- Keep the set versioned. Never overwrite old scores; append a run.

## Metrics

| Layer | Measure |
| --- | --- |
| Retrieval | Recall@k, MRR, hit on expected doc ids |
| Grounding | Faithfulness / contradiction vs context |
| Citations | Cited chunk actually supports the sentence |
| Answer | Key-point coverage; refusal on unanswerable |

- Start with **retrieval recall** before LLM-as-judge. Cheap and stable.
- LLM-as-judge: fixed judge model + rubric. Same judge for A/B.

## Workflow

1. Freeze corpus snapshot (or pin document hashes).
2. Run baseline on `main`.
3. Apply change. Re-run same set and k.
4. Report delta table: metric, baseline, candidate, n.
5. Inspect failures, not only averages.

## Offline vs online

- Offline: golden set in CI for regressions (small subset).
- Online: sample production traces (see `observability`); redact PII first.

## Anti-patterns

- Evaluating only “does it sound good”
- Changing k, prompt, and embedder in one experiment
- Using training documents as the only test questions
---
