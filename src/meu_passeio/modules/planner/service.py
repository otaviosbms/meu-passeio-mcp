"""Fachada do planner usada pelo módulo de trips."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from meu_passeio.modules.mcp.client_manager import current_run_id, current_trip_id
from meu_passeio.modules.planner.graph import PlannerGraph, PlannerState, PlannerStatus
from meu_passeio.modules.planner.llm import PlannerLLMError
from meu_passeio.modules.planner.schemas import TripRequest
from meu_passeio.shared.schemas import TripPlan

logger = logging.getLogger(__name__)


@dataclass
class PlannerResult:
    run_id: str
    status: PlannerStatus
    plan: TripPlan | None = None
    summary: str | None = None
    trip_request: TripRequest | None = None
    questions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class PlannerService:
    def __init__(self, graph: PlannerGraph) -> None:
        self._graph = graph

    async def plan(self, request_text: str, *, trip_id: str | None = None) -> PlannerResult:
        return await self._run({"mode": "create", "request_text": request_text}, trip_id)

    async def revise(
        self, plan: TripPlan, instruction: str, *, trip_id: str | None = None
    ) -> PlannerResult:
        return await self._run(
            {
                "mode": "revise",
                "existing_plan": plan,
                "instruction": instruction,
                "request_text": "",
            },
            trip_id,
        )

    async def _run(self, initial: PlannerState, trip_id: str | None) -> PlannerResult:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        trip_token = current_trip_id.set(trip_id)
        run_token = current_run_id.set(run_id)
        try:
            state = await self._graph.run(initial)
        except PlannerLLMError as exc:
            logger.warning("planner_failed", extra={"workflowRunId": run_id, "error": str(exc)})
            return PlannerResult(run_id=run_id, status="failed", error=str(exc))
        finally:
            current_trip_id.reset(trip_token)
            current_run_id.reset(run_token)

        return PlannerResult(
            run_id=run_id,
            status=state.get("status", "failed"),
            plan=state.get("plan"),
            summary=state.get("summary"),
            trip_request=state.get("trip_request"),
            questions=state.get("questions", []),
            warnings=state.get("warnings", []),
            tool_calls=[
                {"tool": e["tool"], "ok": e["ok"], "error": e["error"]}
                for e in state.get("evidence", [])
            ],
        )
