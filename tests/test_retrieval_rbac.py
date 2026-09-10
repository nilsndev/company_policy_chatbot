"""Isolation tests for the M4 hybrid retrieval pipeline (PRD §6.5): an
IT-department employee's query must never surface Clinical-only policy
content, and vice versa, except company-wide policies. Covers both
independent layers named in CLAUDE.md loop 4 — the SQL-level department
filter and the Neo4j RBAC graph filter — plus supersedes/references handling.
"""

from types import SimpleNamespace

import pytest

from app.services import db, retrieval
from app.services import neo4j as neo4j_service
from app.services.embeddings import EmbeddingClient
from app.services.retrieval import RetrievedChunk

FAKE_SETTINGS = SimpleNamespace(ollama_base_url="http://fake", ollama_embed_model="fake-model")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch: pytest.MonkeyPatch):
    async def fake_embed(self, texts):
        return [[0.0, 0.0, 0.0] for _ in texts]

    monkeypatch.setattr(EmbeddingClient, "embed", fake_embed)


class FakeCursor:
    def __init__(self, rows: list[tuple]):
        self.rows = rows
        self.executed: list[tuple] = []

    async def execute(self, query, params=None):
        self.executed.append((query, params))

    async def fetchall(self):
        return self.rows

    async def fetchone(self):
        return self.rows[0] if self.rows else None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor

    def connection(self):
        return FakeConn(self._cursor)


@pytest.fixture(autouse=True)
def _noop_register_vector(monkeypatch: pytest.MonkeyPatch):
    async def noop(conn):
        return None

    monkeypatch.setattr(retrieval, "register_vector_async", noop)


# ---------------------------------------------------------------------------
# Layer 1: the SQL-level department/role filter runs in the same query as the
# similarity search, parameterized from the server-resolved profile — never
# from anything client-supplied.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_vector_search_parameterizes_department_and_role_from_server_profile():
    cursor = FakeCursor(rows=[("p1", "IT Acceptable Use Policy", 1, None, "content")])
    pool = FakePool(cursor)

    result = await retrieval._vector_search(
        pool, [0.0, 0.0, 0.0], department="IT & Security", role="staff", limit=10
    )

    assert [c.policy_id for c in result] == ["p1"]
    _, params = cursor.executed[0]
    assert params[0] == "IT & Security"
    assert params[1] == "staff"
    assert params[3] == 10


@pytest.mark.anyio
async def test_vector_search_unassigned_profile_only_parameterizes_null_scope():
    # Sam, new hire (PRD persona): no department/role yet. With both params
    # None, "p.department = %s" and "%s = 'compliance_officer'" can never
    # match, leaving only "p.department is null" (company-wide) — enforced by
    # the SQL itself, not extra Python logic.
    cursor = FakeCursor(rows=[])
    pool = FakePool(cursor)

    await retrieval._vector_search(pool, [0.0, 0.0, 0.0], department=None, role=None, limit=10)

    _, params = cursor.executed[0]
    assert params[0] is None
    assert params[1] is None


# ---------------------------------------------------------------------------
# Layer 2: the Neo4j graph filter is independent of layer 1 — even if a
# candidate somehow survives the SQL filter (e.g. a bug in it), the graph
# layer must still deny cross-department content on its own.
# ---------------------------------------------------------------------------


def _make_fake_graph(employees: dict, policies: dict):
    """employees: id -> (department, role). policies: id -> department|None (company-wide)."""

    async def fake_allowed_policy_ids(driver, employee_id, candidate_ids):
        department, role = employees.get(employee_id, (None, None))
        allowed = []
        for pid in candidate_ids:
            policy_department = policies.get(pid)
            if policy_department is None or policy_department == department or role == "compliance_officer":
                allowed.append(pid)
        return allowed

    return fake_allowed_policy_ids


@pytest.mark.anyio
async def test_it_employee_never_sees_clinical_only_content(monkeypatch: pytest.MonkeyPatch):
    it_chunk = RetrievedChunk(policy_id="clinical-1", title="Clinical Safety Policy", version=1, section=None, content="...")
    company_chunk = RetrievedChunk(policy_id="company-1", title="Code of Conduct", version=1, section=None, content="...")

    async def fake_get_profile(pool, employee_id):
        return {"department": "IT & Security", "role": "staff"}

    async def fake_vector_search(pool, query_embedding, department, role, limit):
        # Simulates the SQL filter having (hypothetically) let a Clinical-only
        # chunk through alongside a company-wide one.
        return [it_chunk, company_chunk]

    async def fake_resolve_current_version(driver, policy_id):
        return policy_id

    async def fake_related_policy_ids(driver, policy_id, limit=2):
        return []

    monkeypatch.setattr(db, "get_profile", fake_get_profile)
    monkeypatch.setattr(retrieval, "_vector_search", fake_vector_search)
    monkeypatch.setattr(
        neo4j_service,
        "allowed_policy_ids",
        _make_fake_graph(
            employees={"emp-it": ("IT & Security", "staff")},
            policies={"clinical-1": "Clinical", "company-1": None},
        ),
    )
    monkeypatch.setattr(neo4j_service, "resolve_current_version", fake_resolve_current_version)
    monkeypatch.setattr(neo4j_service, "related_policy_ids", fake_related_policy_ids)

    result = await retrieval.retrieve_chunks(
        pool="fake-pool", driver="fake-driver", settings=FAKE_SETTINGS, employee_id="emp-it", query="q", k=6
    )

    assert [c.policy_id for c in result] == ["company-1"]


@pytest.mark.anyio
async def test_compliance_officer_sees_every_department(monkeypatch: pytest.MonkeyPatch):
    clinical_chunk = RetrievedChunk(policy_id="clinical-1", title="Clinical Safety Policy", version=1, section=None, content="...")
    it_chunk = RetrievedChunk(policy_id="it-1", title="Incident Response Policy", version=1, section=None, content="...")

    async def fake_get_profile(pool, employee_id):
        return {"department": "Compliance & Risk", "role": "compliance_officer"}

    async def fake_vector_search(pool, query_embedding, department, role, limit):
        return [clinical_chunk, it_chunk]

    async def fake_resolve_current_version(driver, policy_id):
        return policy_id

    async def fake_related_policy_ids(driver, policy_id, limit=2):
        return []

    monkeypatch.setattr(db, "get_profile", fake_get_profile)
    monkeypatch.setattr(retrieval, "_vector_search", fake_vector_search)
    monkeypatch.setattr(
        neo4j_service,
        "allowed_policy_ids",
        _make_fake_graph(
            employees={"emp-dana": ("Compliance & Risk", "compliance_officer")},
            policies={"clinical-1": "Clinical", "it-1": "IT & Security"},
        ),
    )
    monkeypatch.setattr(neo4j_service, "resolve_current_version", fake_resolve_current_version)
    monkeypatch.setattr(neo4j_service, "related_policy_ids", fake_related_policy_ids)

    result = await retrieval.retrieve_chunks(
        pool="fake-pool", driver="fake-driver", settings=FAKE_SETTINGS, employee_id="emp-dana", query="q", k=6
    )

    assert {c.policy_id for c in result} == {"clinical-1", "it-1"}


# ---------------------------------------------------------------------------
# Supersedes resolution and REFERENCES enrichment (PRD §6.3, G3).
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_superseded_chunk_is_swapped_for_current_version(monkeypatch: pytest.MonkeyPatch):
    stale_chunk = RetrievedChunk(policy_id="remote-v1", title="Remote Work Policy", version=1, section=None, content="old text")
    current_chunk = RetrievedChunk(policy_id="remote-v2", title="Remote Work Policy", version=2, section=None, content="new text")

    async def fake_get_profile(pool, employee_id):
        return {"department": "HR", "role": "staff"}

    async def fake_vector_search(pool, query_embedding, department, role, limit):
        return [stale_chunk]

    async def fake_allowed_policy_ids(driver, employee_id, candidate_ids):
        return list(candidate_ids)

    async def fake_resolve_current_version(driver, policy_id):
        return "remote-v2" if policy_id == "remote-v1" else policy_id

    async def fake_related_policy_ids(driver, policy_id, limit=2):
        return []

    async def fake_department_scoped_chunk(pool, policy_id, query_embedding, department, role):
        assert policy_id == "remote-v2"
        return current_chunk

    monkeypatch.setattr(db, "get_profile", fake_get_profile)
    monkeypatch.setattr(retrieval, "_vector_search", fake_vector_search)
    monkeypatch.setattr(retrieval, "_department_scoped_chunk", fake_department_scoped_chunk)
    monkeypatch.setattr(neo4j_service, "allowed_policy_ids", fake_allowed_policy_ids)
    monkeypatch.setattr(neo4j_service, "resolve_current_version", fake_resolve_current_version)
    monkeypatch.setattr(neo4j_service, "related_policy_ids", fake_related_policy_ids)

    result = await retrieval.retrieve_chunks(
        pool="fake-pool", driver="fake-driver", settings=FAKE_SETTINGS, employee_id="emp-1", query="q", k=6
    )

    assert [c.policy_id for c in result] == ["remote-v2"]
    assert result[0].content == "new text"


@pytest.mark.anyio
async def test_referenced_policy_added_as_supplementary_and_capped(monkeypatch: pytest.MonkeyPatch):
    primary_chunk = RetrievedChunk(policy_id="incident-1", title="Incident Response Policy", version=1, section=None, content="...")
    related_chunk = RetrievedChunk(policy_id="privacy-1", title="Data Privacy Policy", version=1, section=None, content="...")

    async def fake_get_profile(pool, employee_id):
        return {"department": "IT & Security", "role": "staff"}

    async def fake_vector_search(pool, query_embedding, department, role, limit):
        return [primary_chunk]

    async def fake_allowed_policy_ids(driver, employee_id, candidate_ids):
        return list(candidate_ids)

    async def fake_resolve_current_version(driver, policy_id):
        return policy_id

    async def fake_related_policy_ids(driver, policy_id, limit=2):
        return ["privacy-1"] if policy_id == "incident-1" else []

    async def fake_department_scoped_chunk(pool, policy_id, query_embedding, department, role):
        assert policy_id == "privacy-1"
        return related_chunk

    monkeypatch.setattr(db, "get_profile", fake_get_profile)
    monkeypatch.setattr(retrieval, "_vector_search", fake_vector_search)
    monkeypatch.setattr(retrieval, "_department_scoped_chunk", fake_department_scoped_chunk)
    monkeypatch.setattr(neo4j_service, "allowed_policy_ids", fake_allowed_policy_ids)
    monkeypatch.setattr(neo4j_service, "resolve_current_version", fake_resolve_current_version)
    monkeypatch.setattr(neo4j_service, "related_policy_ids", fake_related_policy_ids)

    result = await retrieval.retrieve_chunks(
        pool="fake-pool", driver="fake-driver", settings=FAKE_SETTINGS, employee_id="emp-1", query="q", k=6
    )

    assert [c.policy_id for c in result] == ["incident-1", "privacy-1"]
    assert result[1].supplementary is True
