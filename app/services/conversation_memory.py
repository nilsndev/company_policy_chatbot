"""History/summary budget for long threads (M5, PRD §6.4, `conversation-memory`
skill).

Working window: raw turns since the conversation's last summary point,
capped by a rough token budget. When that raw window would exceed the
budget, everything except the last `KEEP_RECENT` turns gets folded into a
rolling summary (persisted on `conversations.summary`/`summary_through`);
the kept turns are always sent to the model verbatim alongside the summary.
Triggered only when the budget is exceeded, not on every message — folding
on every turn would mean a summarization LLM call per chat message.
"""

from psycopg_pool import AsyncConnectionPool

from app.services import db
from app.services.llm import LLMClient

RAW_WINDOW_TOKEN_BUDGET = 3000
KEEP_RECENT = 6
CHARS_PER_TOKEN = 4  # rough heuristic for budgeting only, not the model's real tokenizer

_SUMMARY_PROMPT = """Summarize the following conversation between an MHN employee and the \
policy assistant into a short synopsis for the assistant's own future reference: key facts \
established and questions already answered. Do not restate policy text verbatim and do not \
include chain-of-thought. Keep it under 150 words.

{prior_summary_block}Conversation to fold in:
{transcript}"""


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _needs_summarization(raw_messages: list[dict]) -> bool:
    if len(raw_messages) <= KEEP_RECENT:
        return False
    total = sum(estimate_tokens(m["content"]) for m in raw_messages)
    return total > RAW_WINDOW_TOKEN_BUDGET


async def get_context(
    pool: AsyncConnectionPool,
    settings,
    conversation_id: str,
    existing_summary: str | None,
    summary_through: str | None,
    prior_messages: list[dict],
) -> tuple[str | None, list[dict]]:
    """Returns (summary to use, raw turns to send verbatim), given every
    prior message in the conversation. Messages up to `summary_through` are
    already covered by `existing_summary` and excluded from the raw window;
    folds further raw turns into the summary and persists it when that
    window is over budget."""
    raw_messages = [
        m for m in prior_messages if summary_through is None or m["created_at"] > summary_through
    ]
    if not _needs_summarization(raw_messages):
        return existing_summary, raw_messages

    to_fold, to_keep = raw_messages[:-KEEP_RECENT], raw_messages[-KEEP_RECENT:]
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in to_fold)
    prior_block = f"Prior summary:\n{existing_summary}\n\n" if existing_summary else ""
    prompt = _SUMMARY_PROMPT.format(prior_summary_block=prior_block, transcript=transcript)

    llm = LLMClient(settings)
    parts = [chunk async for chunk in llm.stream_chat([{"role": "user", "content": prompt}])]
    new_summary = "".join(parts).strip()

    summarized_through = to_fold[-1]["created_at"]
    await db.update_conversation_summary(pool, conversation_id, new_summary, summarized_through)
    return new_summary, to_keep
