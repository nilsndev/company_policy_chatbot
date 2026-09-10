import json
import logging
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.models.schemas import ChatRequest, ConversationOut, MessageOut
from app.services import conversation_memory, db, retrieval
from app.services.llm import LLMClient
from app.services.retrieval import RetrievedChunk

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = logging.getLogger(__name__)

RETRIEVAL_K = 6

_CITATION_RE = re.compile(r"\[(\d+)\]")

_SYSTEM_PROMPT = """You are the MHN Policy Assistant. Answer the employee's question using ONLY \
the numbered policy excerpts below — do not use outside knowledge and do not invent policies. \
Cite every claim with its bracketed source number, e.g. [1]. If the excerpts don't answer the \
question, say the policy corpus doesn't cover this rather than guessing. \
These excerpts are already scoped to what this employee's department/role may see, and any \
superseded policy has already been resolved to its current version — don't tell the employee \
to double-check with another department or an older/newer version. Excerpts marked \
"(Related policy)" are supplementary context pulled in because a matched policy references \
them; cite one only if it actually helps answer the question.

Policy excerpts:
{context}"""


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _build_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no policy excerpts were found for this question)"
    lines = []
    for i, c in enumerate(chunks, start=1):
        label = "(Related policy) " if c.supplementary else ""
        lines.append(f"[{i}] {label}{c.title} v{c.version} | {c.section or 'General'} | {c.content}")
    return "\n\n".join(lines)


def _extract_citations(text: str, chunks: list[RetrievedChunk]) -> list[dict]:
    seen_indices: set[int] = set()
    citations: list[dict] = []
    for match in _CITATION_RE.finditer(text):
        index = int(match.group(1))
        if index in seen_indices or not (1 <= index <= len(chunks)):
            continue
        seen_indices.add(index)
        chunk = chunks[index - 1]
        citations.append(
            {
                "index": index,
                "policy_id": chunk.policy_id,
                "title": chunk.title,
                "version": chunk.version,
                "section": chunk.section,
            }
        )
    return citations


@router.get("/conversations")
async def get_conversations(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> list[ConversationOut]:
    rows = await db.list_conversations(request.app.state.db_pool, user.id)
    return [ConversationOut(**row) for row in rows]


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str, request: Request, user: CurrentUser = Depends(get_current_user)
) -> list[MessageOut]:
    pool = request.app.state.db_pool
    owned = await db.get_conversation(pool, user.id, conversation_id)
    if not owned:
        raise HTTPException(status_code=404, detail="conversation not found")
    rows = await db.list_messages(pool, conversation_id)
    return [MessageOut(**row) for row in rows]


@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    pool = request.app.state.db_pool

    conversation_id = body.conversation_id
    existing_summary: str | None = None
    summary_through: str | None = None
    if conversation_id:
        owned = await db.get_conversation(pool, user.id, conversation_id)
        if not owned:
            raise HTTPException(status_code=404, detail="conversation not found")
        existing_summary = owned["summary"]
        summary_through = owned["summary_through"]
    else:
        title = body.message[:60]
        conversation_id = await db.create_conversation(pool, user.id, title)

    # A brand-new thread (no conversation_id in the request) never inherits
    # another thread's history — `prior` stays empty, not just filtered.
    prior = await db.list_messages(pool, conversation_id) if body.conversation_id else []
    await db.append_message(pool, conversation_id, "user", body.message)

    try:
        retrieved = await retrieval.retrieve_chunks(
            pool=pool,
            driver=request.app.state.neo4j_driver,
            settings=settings,
            employee_id=user.id,
            query=body.message,
            k=RETRIEVAL_K,
        )
    except Exception:  # noqa: BLE001 - retrieval failure degrades to ungrounded chat, not an error
        logger.exception("retrieval failed, falling back to ungrounded chat")
        retrieved = []

    prior_for_memory = [{"role": m["role"], "content": m["content"], "created_at": m["created_at"]} for m in prior]
    summary, kept_raw = await conversation_memory.get_context(
        pool, settings, conversation_id, existing_summary, summary_through, prior_for_memory
    )

    system_prompt = _SYSTEM_PROMPT.format(context=_build_context(retrieved))
    if summary:
        system_prompt += f"\n\nSummary of the earlier part of this conversation:\n{summary}"
    system_message = {"role": "system", "content": system_prompt}

    history = [{"role": m["role"], "content": m["content"]} for m in kept_raw]
    history.append({"role": "user", "content": body.message})
    llm_messages = [system_message, *history]

    async def event_stream() -> AsyncIterator[str]:
        llm = LLMClient(settings)
        stream = llm.stream_chat(llm_messages)
        parts: list[str] = []
        citations: list[dict] = []
        try:
            async for token in stream:
                if await request.is_disconnected():
                    break
                parts.append(token)
                yield _sse("token", {"text": token})
        except Exception:  # noqa: BLE001 - surfaced to client, not a stack trace
            yield _sse("error", {"message": "the model is unavailable right now"})
            return
        finally:
            # Explicitly close the provider stream rather than leaving it for
            # GC: a `break` above (client disconnected/Stop clicked) would
            # otherwise leave the Ollama request running until the async
            # generator happens to get garbage-collected.
            await stream.aclose()
            full_text = "".join(parts)
            if full_text:
                citations = _extract_citations(full_text, retrieved)
                await db.append_message(pool, conversation_id, "assistant", full_text, citations)

        for citation in citations:
            yield _sse("citation", citation)

        yield _sse("done", {"conversation_id": conversation_id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
