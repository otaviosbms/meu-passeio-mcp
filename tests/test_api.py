"""Testes ponta a ponta da API com o MCP Server do Meu Passeio real (stdio)."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import SERVER
from fastapi.testclient import TestClient

from meu_passeio.api.main import create_app
from meu_passeio.core.config import Settings

PLAN = {
    "title": "Bate-volta em Garça",
    "origin": "Marília, SP",
    "destination": "Garça, SP",
    "start_date": "2027-01-09",
    "end_date": "2027-01-09",
    "travelers": 2,
    "budget": {"total": 400},
    "itinerary": [
        {
            "day_number": 1,
            "date": "2027-01-09",
            "activities": [{"id": "a1", "name": "Lago", "start_time": "09:00"}],
        }
    ],
}


@pytest.fixture
def client(tmp_path: Path, mcp_test_config: Path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        mcp_config_path=mcp_test_config,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health_and_mcp_catalog(client: TestClient):
    health = client.get("/health").json()
    assert health["mcp_servers"][SERVER] == "connected"
    assert health["status"] == "degraded"  # o server "broken" falhou, mas a API segue

    tools = client.get("/mcp/tools").json()
    assert {t["server"] for t in tools} == {SERVER}
    assert len(tools) == 28

    call = client.post(
        f"/mcp/tools/{SERVER}/calculate_budget_breakdown", json={"total_budget": 400, "days": 2}
    ).json()
    assert call["ok"] and call["data"]["per_person_per_day"] == 200

    invalid = client.post(
        f"/mcp/tools/{SERVER}/calculate_budget_breakdown", json={"days": 0}
    ).json()
    assert not invalid["ok"] and "inválidos" in invalid["error"]


def test_trip_crud(client: TestClient):
    created = client.post("/trips", json={"plan": PLAN})
    assert created.status_code == 201, created.text
    trip = created.json()
    assert trip["title"] == "Bate-volta em Garça"
    assert trip["plan"]["itinerary"][0]["activities"][0]["name"] == "Lago"

    assert [t["id"] for t in client.get("/trips").json()] == [trip["id"]]

    updated_plan = {**PLAN, "title": "Bate-volta revisado"}
    updated = client.put(f"/trips/{trip['id']}", json={"plan": updated_plan}).json()
    assert updated["title"] == "Bate-volta revisado"

    assert client.delete(f"/trips/{trip['id']}").status_code == 204
    assert client.get(f"/trips/{trip['id']}").status_code == 404


def test_trip_rejects_invalid_plan(client: TestClient):
    response = client.post("/trips", json={"plan": {**PLAN, "travelers": 0}})
    assert response.status_code == 422
