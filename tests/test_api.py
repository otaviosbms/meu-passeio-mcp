"""Testes ponta a ponta da API com um LLM falso e o Budget MCP Server real (stdio)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from meu_passeio.api.main import create_app
from meu_passeio.core.config import Settings
from meu_passeio.modules.planner.schemas import ItineraryOutput, ParsedBudget, TripRequest
from meu_passeio.shared.schemas import Budget, CostEstimate, TripActivity, TripDay, TripPlan


class FakeLLM:
    """Simula o Claude: parser -> 1 tool call MCP -> resumo -> itinerário estruturado."""

    def __init__(self, *, ask_clarification: bool = False) -> None:
        self.ask_clarification = ask_clarification
        self.research_calls = 0
        self.tool_results: list[Any] = []

    async def parse(self, *, system: str, messages: list[dict[str, Any]], output_format: type):
        if output_format is TripRequest:
            if self.ask_clarification and "Respostas do usuário" not in messages[0]["content"]:
                return TripRequest(trip_type="other", clarification_questions=["Para onde?"])
            return TripRequest(
                trip_type="day_trip",
                origin="Marília, SP",
                destination="Garça, SP",
                start_date=date(2027, 1, 9),
                duration_days=1,
                travelers=2,
                budget=ParsedBudget(amount=400),
                preferences=["natureza"],
            )
        assert output_format is ItineraryOutput
        content = messages[0]["content"]
        assert "budget__calculate_budget_breakdown" in content  # evidência chegou ao builder
        title = "Bate-volta revisado" if "MODO REVISÃO" in content else "Bate-volta em Garça"
        return ItineraryOutput(
            summary="Dia de natureza.",
            plan=TripPlan(
                title=title,
                origin="Marília, SP",
                destination="Garça, SP",
                start_date=date(2027, 1, 9),
                end_date=date(2027, 1, 9),
                travelers=2,
                budget=Budget(total=400),
                itinerary=[
                    TripDay(
                        day_number=1,
                        date=date(2027, 1, 9),
                        activities=[
                            TripActivity(
                                id="a1", name="Lago", start_time="09:00", duration_minutes=90
                            )
                        ],
                    )
                ],
                cost_estimates=[CostEstimate(category="food", amount=160)],
            ),
        )

    async def create(self, *, system: str, messages: list[dict[str, Any]], tools: list[dict]):
        assert any(t["name"] == "budget__calculate_budget_breakdown" for t in tools)
        self.research_calls += 1
        last = messages[-1]["content"]
        if isinstance(last, list):  # voltou com tool_result
            self.tool_results.extend(last)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text="Resumo: orçamento distribuído.")],
            )
        return SimpleNamespace(
            stop_reason="tool_use",
            content=[
                SimpleNamespace(
                    type="tool_use",
                    id="toolu_1",
                    name="budget__calculate_budget_breakdown",
                    input={"total_budget": 400, "days": 1, "travelers": 2},
                )
            ],
        )


@pytest.fixture
def make_client(tmp_path: Path, budget_only_config: Path):
    def _make(llm: FakeLLM) -> TestClient:
        settings = Settings(
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
            mcp_config_path=budget_only_config,
        )
        return TestClient(create_app(settings, llm=llm))  # type: ignore[arg-type]

    return _make


def test_health_and_mcp_catalog(make_client):
    with make_client(FakeLLM()) as client:
        health = client.get("/health").json()
        assert health["mcp_servers"]["budget"] == "connected"
        assert health["status"] == "degraded"  # o server "broken" falhou, mas a API segue
        tools = client.get("/mcp/tools").json()
        assert {t["server"] for t in tools} == {"budget"}
        call = client.post(
            "/mcp/tools/budget/calculate_budget_breakdown", json={"total_budget": 400, "days": 2}
        ).json()
        assert call["ok"] and call["data"]["per_person_per_day"] == 200


def test_create_trip_runs_planner_with_mcp_tools(make_client):
    llm = FakeLLM()
    with make_client(llm) as client:
        response = client.post(
            "/trips", json={"request": "Bate-volta saindo de Marília com natureza, R$ 400"}
        )
        assert response.status_code == 201, response.text
        trip = response.json()
        assert trip["status"] == "completed"
        assert trip["title"] == "Bate-volta em Garça"
        assert trip["plan"]["itinerary"][0]["activities"][0]["name"] == "Lago"
        # o tool_result veio do Budget MCP Server real
        assert llm.tool_results and llm.tool_results[0]["is_error"] is False
        assert "per_person_per_day" in llm.tool_results[0]["content"]

        listed = client.get("/trips").json()
        assert [t["id"] for t in listed] == [trip["id"]]

        revised = client.post(
            f"/trips/{trip['id']}/revise", json={"instruction": "Troque o almoço"}
        ).json()
        assert revised["title"] == "Bate-volta revisado"
        assert len(revised["revisions"]) == 1

        assert client.delete(f"/trips/{trip['id']}").status_code == 204
        assert client.get(f"/trips/{trip['id']}").status_code == 404


def test_clarification_flow(make_client):
    with make_client(FakeLLM(ask_clarification=True)) as client:
        trip = client.post("/trips", json={"request": "Quero viajar"}).json()
        assert trip["status"] == "needs_clarification"
        assert "Para onde?" in trip["questions"]

        answered = client.post(
            f"/trips/{trip['id']}/clarify", json={"answer": "Garça, saindo de Marília, 1 dia"}
        ).json()
        assert answered["status"] == "completed"

        conflict = client.post(f"/trips/{trip['id']}/clarify", json={"answer": "x"})
        assert conflict.status_code == 409
