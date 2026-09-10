from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from app.services import conversation_memory, db
from app.services.llm import LLMClient

FAKE_SETTINGS = SimpleNamespace(ollama_base_url="http://fake", ollama_chat_model="fake-model")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _message(role: str, content: str, created_at: str) -> dict:
    return {"role": role, "content": content, "created_at": created_at}


@pytest.mark.anyio
async def test_under_budget_returns_full_history_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("must not summarize when under budget")

    monkeypatch.setattr(db, "update_conversation_summary", fail_if_called)

    raw = [_message("user", "hi", "2026-01-01T00:00:00+00:00")]
    summary, kept = await conversation_memory.get_context(
        pool="fake-pool", settings=None, conversation_id="c1", existing_summary=None,
        summary_through=None, prior_messages=raw,
    )

    assert summary is None
    assert kept == raw


@pytest.mark.anyio
async def test_messages_before_summary_through_are_excluded_from_raw_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("must not summarize when the remaining raw window is under budget")

    monkeypatch.setattr(db, "update_conversation_summary", fail_if_called)

    prior = [
        _message("user", "old turn, already folded into the summary", "2026-01-01T00:00:00+00:00"),
        _message("user", "new turn, after summary_through", "2026-01-02T00:00:00+00:00"),
    ]
    summary, kept = await conversation_memory.get_context(
        pool="fake-pool", settings=None, conversation_id="c1", existing_summary="old stuff happened",
        summary_through="2026-01-01T12:00:00+00:00", prior_messages=prior,
    )

    assert summary == "old stuff happened"
    assert kept == [prior[1]]


@pytest.mark.anyio
async def test_over_budget_folds_older_turns_and_persists_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    # Long enough messages to exceed RAW_WINDOW_TOKEN_BUDGET, and more of them
    # than KEEP_RECENT so there's something to fold.
    long_text = "x" * 2000
    raw = [
        _message("user" if i % 2 == 0 else "assistant", long_text, f"2026-01-01T00:{i:02d}:00+00:00")
        for i in range(10)
    ]

    async def fake_stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        for token in ["folded ", "summary"]:
            yield token

    captured: dict = {}

    async def fake_update_summary(pool, conversation_id, summary, summary_through):
        captured["conversation_id"] = conversation_id
        captured["summary"] = summary
        captured["summary_through"] = summary_through

    monkeypatch.setattr(LLMClient, "stream_chat", fake_stream_chat)
    monkeypatch.setattr(db, "update_conversation_summary", fake_update_summary)

    summary, kept = await conversation_memory.get_context(
        pool="fake-pool", settings=FAKE_SETTINGS, conversation_id="c1", existing_summary=None,
        summary_through=None, prior_messages=raw,
    )

    assert summary == "folded summary"
    assert kept == raw[-conversation_memory.KEEP_RECENT :]
    assert captured["conversation_id"] == "c1"
    assert captured["summary"] == "folded summary"
    assert captured["summary_through"] == raw[-conversation_memory.KEEP_RECENT - 1]["created_at"]
