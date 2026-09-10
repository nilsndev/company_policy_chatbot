from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.services import db, llm, retrieval
from app.services.retrieval import RetrievedChunk


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_auth():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="user-1", email="a@b.com")
    app.state.db_pool = "fake-pool"  # unused directly; db calls are monkeypatched below
    app.state.neo4j_driver = "fake-driver"  # unused directly; retrieval is monkeypatched below
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _fake_db(monkeypatch: pytest.MonkeyPatch):
    async def fake_create_conversation(pool, user_id, title):
        return "conv-1"

    async def fake_get_conversation(pool, user_id, conversation_id):
        return {"id": conversation_id, "summary": None, "summary_through": None}

    async def fake_list_messages(pool, conversation_id):
        return []

    async def fake_append_message(pool, conversation_id, role, content, citations=None):
        return None

    async def fake_retrieve_chunks(pool, driver, settings, employee_id, query, k=6):
        return []

    monkeypatch.setattr(db, "create_conversation", fake_create_conversation)
    monkeypatch.setattr(db, "get_conversation", fake_get_conversation)
    monkeypatch.setattr(db, "list_messages", fake_list_messages)
    monkeypatch.setattr(db, "append_message", fake_append_message)
    monkeypatch.setattr(retrieval, "retrieve_chunks", fake_retrieve_chunks)


async def _fake_stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
    for token in ["Hel", "lo"]:
        yield token


@pytest.mark.anyio
async def test_chat_streams_tokens_and_done(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm.LLMClient, "stream_chat", _fake_stream_chat)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/v1/chat",
            json={"conversation_id": None, "message": "hi"},
            headers={"Authorization": "Bearer x"},
        ) as response:
            assert response.status_code == 200
            body = "".join([chunk async for chunk in response.aiter_text()])

    assert "event: token" in body
    assert '"text": "Hel"' in body
    assert "event: done" in body
    assert '"conversation_id": "conv-1"' in body


@pytest.mark.anyio
async def test_chat_grounded_reply_emits_citation(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = RetrievedChunk(
        policy_id="policy-1", title="Remote Work Policy", version=2, section="Location", content="..."
    )

    async def fake_retrieve_chunks(pool, driver, settings, employee_id, query, k=6):
        return [chunk]

    async def fake_stream_chat_with_citation(self, messages: list[dict]) -> AsyncIterator[str]:
        for token in ["Yes, see ", "[1]", "."]:
            yield token

    captured: dict = {}

    async def fake_append_message(pool, conversation_id, role, content, citations=None):
        if role == "assistant":
            captured["citations"] = citations

    monkeypatch.setattr(retrieval, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(llm.LLMClient, "stream_chat", fake_stream_chat_with_citation)
    monkeypatch.setattr(db, "append_message", fake_append_message)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/v1/chat",
            json={"conversation_id": None, "message": "can I work remotely?"},
            headers={"Authorization": "Bearer x"},
        ) as response:
            body = "".join([chunk async for chunk in response.aiter_text()])

    assert "event: citation" in body
    assert '"policy_id": "policy-1"' in body
    assert '"title": "Remote Work Policy"' in body
    assert captured["citations"] == [
        {
            "index": 1,
            "policy_id": "policy-1",
            "title": "Remote Work Policy",
            "version": 2,
            "section": "Location",
        }
    ]


@pytest.mark.anyio
async def test_chat_continuing_conversation_includes_summary_and_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_conversation(pool, user_id, conversation_id):
        return {
            "id": conversation_id,
            "summary": "Earlier: employee asked about leave policy.",
            "summary_through": None,
        }

    async def fake_list_messages(pool, conversation_id):
        return [
            {
                "id": "m1",
                "role": "user",
                "content": "What is the leave policy?",
                "created_at": "2026-01-01T00:00:00+00:00",
                "citations": [],
            },
            {
                "id": "m2",
                "role": "assistant",
                "content": "You get 20 days.",
                "created_at": "2026-01-01T00:00:05+00:00",
                "citations": [],
            },
        ]

    captured: dict = {}

    async def fake_stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        captured["messages"] = messages
        yield "OK"

    monkeypatch.setattr(db, "get_conversation", fake_get_conversation)
    monkeypatch.setattr(db, "list_messages", fake_list_messages)
    monkeypatch.setattr(llm.LLMClient, "stream_chat", fake_stream_chat)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/v1/chat",
            json={"conversation_id": "conv-existing", "message": "and sick leave?"},
            headers={"Authorization": "Bearer x"},
        ) as response:
            assert response.status_code == 200
            _ = "".join([chunk async for chunk in response.aiter_text()])

    llm_messages = captured["messages"]
    assert "Earlier: employee asked about leave policy." in llm_messages[0]["content"]
    assert {"role": "user", "content": "What is the leave policy?"} in llm_messages
    assert {"role": "assistant", "content": "You get 20 days."} in llm_messages
    assert llm_messages[-1] == {"role": "user", "content": "and sick leave?"}


@pytest.mark.anyio
async def test_chat_new_thread_does_not_include_other_conversations_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_list_messages_should_not_be_called(pool, conversation_id):
        raise AssertionError("list_messages must not be called for a brand-new thread")

    captured: dict = {}

    async def fake_stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        captured["messages"] = messages
        yield "OK"

    monkeypatch.setattr(db, "list_messages", fake_list_messages_should_not_be_called)
    monkeypatch.setattr(llm.LLMClient, "stream_chat", fake_stream_chat)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/v1/chat",
            json={"conversation_id": None, "message": "hi"},
            headers={"Authorization": "Bearer x"},
        ) as response:
            assert response.status_code == 200
            _ = "".join([chunk async for chunk in response.aiter_text()])

    # Only the system message and the new user turn — nothing from any prior thread.
    assert len(captured["messages"]) == 2
    assert captured["messages"][-1] == {"role": "user", "content": "hi"}


@pytest.mark.anyio
async def test_chat_unknown_conversation_404() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # override get_conversation to simulate not-owned/not-found for this one call
        from app.services import db as db_module

        original = db_module.get_conversation

        async def not_found(pool, user_id, conversation_id):
            return None

        db_module.get_conversation = not_found
        try:
            response = await client.post(
                "/api/v1/chat",
                json={"conversation_id": "missing", "message": "hi"},
                headers={"Authorization": "Bearer x"},
            )
        finally:
            db_module.get_conversation = original

    assert response.status_code == 404
