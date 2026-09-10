import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.services import db
from app.services import neo4j as neo4j_service


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_auth(monkeypatch: pytest.MonkeyPatch):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="user-1", email="a@b.com")
    app.state.db_pool = "fake-pool"  # unused directly; db calls are monkeypatched below
    app.state.neo4j_driver = "fake-driver"  # unused directly; neo4j calls are monkeypatched below

    async def fake_upsert_employee(driver, employee_id, department, role):
        return None

    monkeypatch.setattr(neo4j_service, "upsert_employee", fake_upsert_employee)
    yield
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_get_profile_none(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_profile(pool, user_id):
        assert user_id == "user-1"
        return None

    monkeypatch.setattr(db, "get_profile", fake_get_profile)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/profile", headers={"Authorization": "Bearer x"})

    assert response.status_code == 200
    assert response.json() == {"id": "user-1", "department": None, "role": None}


@pytest.mark.anyio
async def test_set_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_upsert(pool, user_id, department, role):
        return {"department": department, "role": role}

    monkeypatch.setattr(db, "upsert_profile", fake_upsert)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/profile",
            json={"department": "Clinical", "role": "staff"},
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 200
    assert response.json() == {"id": "user-1", "department": "Clinical", "role": "staff"}


@pytest.mark.anyio
async def test_set_profile_syncs_employee_to_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_upsert(pool, user_id, department, role):
        return {"department": department, "role": role}

    monkeypatch.setattr(db, "upsert_profile", fake_upsert)

    calls = []

    async def fake_upsert_employee(driver, employee_id, department, role):
        calls.append((employee_id, department, role))

    monkeypatch.setattr(neo4j_service, "upsert_employee", fake_upsert_employee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/profile",
            json={"department": "Clinical", "role": "staff"},
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 200
    assert calls == [("user-1", "Clinical", "staff")]


@pytest.mark.anyio
async def test_set_profile_succeeds_despite_graph_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_upsert(pool, user_id, department, role):
        return {"department": department, "role": role}

    monkeypatch.setattr(db, "upsert_profile", fake_upsert)

    async def failing_upsert_employee(driver, employee_id, department, role):
        raise RuntimeError("graph unreachable")

    monkeypatch.setattr(neo4j_service, "upsert_employee", failing_upsert_employee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/profile",
            json={"department": "Clinical", "role": "staff"},
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 200
    assert response.json() == {"id": "user-1", "department": "Clinical", "role": "staff"}


@pytest.mark.anyio
async def test_missing_token_rejected() -> None:
    app.dependency_overrides.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/profile")
    assert response.status_code == 401
