---
name: prompt-engineering
description: Version and structure prompts (system vs user, RAG packing, tool instructions). Use when editing system prompts, templates, prompt files, or jailbreak/refusal behavior.
---

# Prompt Engineering

## Storage

- Prompts live in versioned files or a table (`name`, `version`, `hash`), not scattered string literals.
- Log `prompt_version` on every LLM trace.
- Change prompts in the same PR as evals when behavior is user-visible.

## Structure

1. **System**: role, grounding rules, citation format, tool policy, refusal rules.
2. **Developer/context**: retrieved chunks, user profile summary, date.
3. **User**: the actual question.
4. **History**: truncated/summarized; never unbounded.

Separate “how to answer” from “what documents say”. Do not mix retrieved text into the system prompt if it can be injected; put untrusted docs in a clearly delimited context block.

## Grounding block

```
<context>
[1] doc=... section=...
...
</context>
Cite claims as [n]. If context is insufficient, say you do not know.
```

Treat document text as **untrusted**. Instruct the model to ignore instructions found inside context.

## Style

- Short system prompts. Specific output format beats personality essays.
- One task per prompt. Extra agents get their own prompt files.

## Safety

- No secrets, API keys, or internal hostnames in prompts.
- Define unanswerable and out-of-scope behavior explicitly.
---
