---
name: rag-engineering
description: Design and implement retrieval-augmented generation (chunking, embeddings, hybrid search, rerank, citations). Use when adding RAG, retrieval, vector search, chunking, embeddings, rerankers, or citation grounding.
---

# RAG Engineering

## Defaults

- Store documents in Postgres + pgvector (via Supabase). Do not add a second vector DB unless the user asks.
- Embed with one model only. Put the model name in config, not hardcoded in retrieval code.
- Always return **source ids + spans** with answers. Never invent citations.
- Retrieval is hybrid: BM25/keyword + dense, then rerank. Dense-only is a fallback.

## Indexing

1. Extract text with a dedicated loader (PDF, HTML, markdown, DOCX). Fail a file; do not silently skip.
2. Chunk by structure first (headings, sections), then token size. Default: 400–800 tokens, 10–15% overlap.
3. Persist `document_id`, `chunk_index`, `source_uri`, `hash`, `metadata` on every chunk.
4. Reindex is **idempotent**: hash content; skip unchanged chunks; delete orphans for a document.
5. Never embed PII-heavy fields without an explicit redaction step.

## Query path

```
query → rewrite/expand (optional) → hybrid retrieve k=20–40
     → rerank top n=5–8 → pack context with citations → generate
```

- Apply metadata filters **before** vector search (tenant, doc type, date).
- If retrieval scores are all low, say so and answer from general knowledge only when the user allows it.
- Cap context tokens. Drop lowest-ranked chunks rather than truncating mid-chunk.

## Generation

- System prompt: answer only from provided context; quote or cite chunk ids.
- Pass chunks as numbered blocks: `[n] source | section | text`.
- Stream the answer; attach citations after or inline as `[n]`.

## Anti-patterns

- Stuffing full documents into the prompt
- One giant “miscellaneous” namespace with no tenant/user filter
- Re-embedding the corpus on every query
- Mixing embedding models in the same table

## Additional resources

- Evaluation workflow: `rag-evaluation`
- Ingest jobs: `ingestion-pipeline`
- Vector/RLS details: `supabase` and `pgvector-search`
---
