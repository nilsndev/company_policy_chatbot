---
name: evaluation
description: RAG evaluation (golden sets, recall, faithfulness, citation accuracy). Use when measuring retrieval/answer quality, comparing chunking or prompts, or claiming an improvement.
---

# Evaluation

**Rule:** Do not claim a retrieval or prompt change is better unless an eval ran or the user waived it.

## When to use

New golden questions, metric code, A/B of chunker/retriever/prompt, CI eval job. Implementation of retrieve: `rag`. Judge LLM: `llm`.

## Golden set

JSON/YAML: `question`, `expected_doc_ids`, optional `expected_answer_points`, `forbidden_claims`. Cover lookup, multi-hop, unanswerable, injection, **tenant isolation**. Version the set; append runs, do not overwrite history.

## Metrics (in order)

1. Retrieval **Recall@k** / hit on expected docs (cheap, stable).
2. Citation support: cited `[n]` exists in retrieved chunks and backs the sentence.
3. Faithfulness vs context (LLM-as-judge: **fixed** judge model + rubric).
4. Key-point coverage; refusal on unanswerable.

Change **one** of k, prompt, chunker, embedder per experiment. Pin corpus hashes.

## CI

- PR: mocked unit tests (`testing`).
- Nightly or `eval` label: small golden subset. Never embed the full corpus in GitHub Actions.

## Do not

- “Sounds good” as the only metric, or paid APIs on every PR.
---
