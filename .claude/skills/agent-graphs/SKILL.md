---
name: agent-graphs
description: Multi-step agent graphs (plan → retrieve → tool → answer, LangGraph-style). Use when adding agents, graphs, routers, multi-hop RAG, or tool-using workflows beyond a single LLM call.
---

# Agent Graphs

## When to use a graph

- Single retrieve-then-generate: **no graph**. Keep a function pipeline.
- Graph when you need branching: clarify question, web+RAG, reviewer, or multi-tool plans.

## Nodes (typical chatbot)

```
route → (retrieve | clarify | refuse)
     → synthesize → (optional) verify citations → stream
```

- Each node has typed state: `messages`, `chunks`, `user_id`, `citations`.
- Nodes are unit-testable without HTTP.

## Control

- Max steps and max tools. Cycle detection on repeated tool+args.
- Human-in-the-loop before irreversible tools.
- Persist graph state for resume only if the product needs it; otherwise keep state in the request.

## Implementation

- Prefer an explicit state machine or LangGraph. Do not nest ad hoc `while True` tool loops in the router.
- Log each node name and I/O sizes (see `observability`).

## Do not

- Give the agent unconstrained code execution.
- Re-retrieve the whole corpus on every hop without tightening the query.
---
