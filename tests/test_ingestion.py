import pytest

from app.core.config import Settings
from app.services import db, embeddings, ingestion, storage


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


SAMPLE_DOC = b"""---
title: Sample Policy
version: 1
---

## Purpose

Say hello.
"""


@pytest.mark.anyio
async def test_process_job_ready_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict = {}

    async def fake_claim(pool, job_id):
        return "policy-1"

    async def fake_source(pool, policy_id):
        return {"storage_path": "sample.md", "content_hash": "hash-new"}

    async def fake_download(settings, path):
        return SAMPLE_DOC

    async def fake_latest_hash(pool, policy_id):
        return "hash-old"  # different from current -> must reprocess

    async def fake_embed(self, texts):
        return [[0.1, 0.2] for _ in texts]

    async def fake_replace(pool, policy_id, chunks, embeds, model, content_hash):
        calls["replace"] = (policy_id, len(chunks), len(embeds), model, content_hash)

    async def fake_mark(pool, job_id, status, error=None):
        calls["mark"] = (job_id, status, error)

    monkeypatch.setattr(db, "claim_ingestion_job", fake_claim)
    monkeypatch.setattr(db, "get_policy_source", fake_source)
    monkeypatch.setattr(db, "get_latest_chunk_hash", fake_latest_hash)
    monkeypatch.setattr(db, "replace_policy_chunks", fake_replace)
    monkeypatch.setattr(db, "mark_ingestion_job", fake_mark)
    monkeypatch.setattr(storage, "download_object", fake_download)
    monkeypatch.setattr(embeddings.EmbeddingClient, "embed", fake_embed)

    await ingestion.process_job(pool="fake-pool", settings=Settings(), job_id="job-1")

    assert calls["replace"][0] == "policy-1"
    assert calls["replace"][3] == Settings().ollama_embed_model
    assert calls["replace"][4] == "hash-new"
    assert calls["mark"] == ("job-1", "ready", None)


@pytest.mark.anyio
async def test_process_job_skips_unchanged_content(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict = {}

    async def fake_claim(pool, job_id):
        return "policy-1"

    async def fake_source(pool, policy_id):
        return {"storage_path": "sample.md", "content_hash": "same-hash"}

    async def fake_latest_hash(pool, policy_id):
        return "same-hash"

    async def fake_replace(*args, **kwargs):
        calls["replace_called"] = True

    async def fake_mark(pool, job_id, status, error=None):
        calls["mark"] = (job_id, status, error)

    async def fail_if_downloaded(*args, **kwargs):
        raise AssertionError("should not download an unchanged file")

    monkeypatch.setattr(db, "claim_ingestion_job", fake_claim)
    monkeypatch.setattr(db, "get_policy_source", fake_source)
    monkeypatch.setattr(db, "get_latest_chunk_hash", fake_latest_hash)
    monkeypatch.setattr(db, "replace_policy_chunks", fake_replace)
    monkeypatch.setattr(db, "mark_ingestion_job", fake_mark)
    monkeypatch.setattr(storage, "download_object", fail_if_downloaded)

    await ingestion.process_job(pool="fake-pool", settings=Settings(), job_id="job-1")

    assert "replace_called" not in calls
    assert calls["mark"] == ("job-1", "ready", None)


@pytest.mark.anyio
async def test_process_job_marks_failed_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict = {}

    async def fake_claim(pool, job_id):
        return "policy-1"

    async def fake_source(pool, policy_id):
        raise RuntimeError("storage unreachable")

    async def fake_mark(pool, job_id, status, error=None):
        calls["mark"] = (job_id, status, error)

    monkeypatch.setattr(db, "claim_ingestion_job", fake_claim)
    monkeypatch.setattr(db, "get_policy_source", fake_source)
    monkeypatch.setattr(db, "mark_ingestion_job", fake_mark)

    await ingestion.process_job(pool="fake-pool", settings=Settings(), job_id="job-1")

    assert calls["mark"][0] == "job-1"
    assert calls["mark"][1] == "failed"
    assert "storage unreachable" in calls["mark"][2]


@pytest.mark.anyio
async def test_process_job_noop_when_already_claimed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_claim(pool, job_id):
        return None

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("should not be called when claim fails")

    monkeypatch.setattr(db, "claim_ingestion_job", fake_claim)
    monkeypatch.setattr(db, "get_policy_source", fail_if_called)

    await ingestion.process_job(pool="fake-pool", settings=Settings(), job_id="job-1")
