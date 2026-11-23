"""Regras de negócio de viagens: cria, esclarece, revisa e persiste planos."""

from __future__ import annotations

from datetime import UTC, datetime

from meu_passeio.modules.planner.service import PlannerResult, PlannerService
from meu_passeio.modules.trips.models import Trip
from meu_passeio.modules.trips.repository import TripRepository
from meu_passeio.shared.schemas import TripPlan


class TripNotFound(LookupError):
    pass


class InvalidTripState(ValueError):
    pass


class TripService:
    def __init__(self, repository: TripRepository, planner: PlannerService) -> None:
        self._repo = repository
        self._planner = planner

    @staticmethod
    def _apply(trip: Trip, result: PlannerResult) -> None:
        trip.status = result.status
        trip.last_run_id = result.run_id
        trip.last_error = result.error
        trip.questions = result.questions
        trip.warnings = result.warnings
        if result.trip_request is not None:
            trip.trip_request = result.trip_request.model_dump(mode="json")
        if result.plan is not None:
            trip.plan = result.plan.model_dump(mode="json")
            trip.title = result.plan.title or trip.title
        if result.summary:
            trip.summary = result.summary

    async def create(self, request_text: str) -> Trip:
        trip = await self._repo.add(Trip(request_text=request_text, status="planning"))
        result = await self._planner.plan(request_text, trip_id=trip.id)
        self._apply(trip, result)
        return await self._repo.save(trip)

    async def clarify(self, trip_id: str, answer: str) -> Trip:
        trip = await self.get(trip_id)
        if trip.status != "needs_clarification":
            raise InvalidTripState("Esta viagem não está aguardando esclarecimentos.")
        questions = "\n".join(f"- {q}" for q in trip.questions)
        trip.request_text = (
            f"{trip.request_text}\n\nPerguntas do planejador:\n{questions}\n\n"
            f"Respostas do usuário:\n{answer}"
        )
        result = await self._planner.plan(trip.request_text, trip_id=trip.id)
        self._apply(trip, result)
        return await self._repo.save(trip)

    async def revise(self, trip_id: str, instruction: str) -> Trip:
        trip = await self.get(trip_id)
        if not trip.plan:
            raise InvalidTripState("A viagem ainda não tem um roteiro para revisar.")
        current = TripPlan.model_validate(trip.plan)
        result = await self._planner.revise(current, instruction, trip_id=trip.id)
        if result.status != "completed" or result.plan is None:
            # Mantém o roteiro anterior intacto em caso de falha.
            trip.last_error = result.error or "Não foi possível revisar o roteiro."
            trip.last_run_id = result.run_id
            return await self._repo.save(trip)
        trip.revisions = [
            *trip.revisions,
            {
                "instruction": instruction,
                "run_id": result.run_id,
                "at": datetime.now(UTC).isoformat(),
                "previous_plan": trip.plan,
            },
        ]
        self._apply(trip, result)
        return await self._repo.save(trip)

    async def get(self, trip_id: str) -> Trip:
        trip = await self._repo.get(trip_id)
        if trip is None:
            raise TripNotFound(trip_id)
        return trip

    async def list(self, limit: int, offset: int) -> list[Trip]:
        return await self._repo.list(limit=limit, offset=offset)

    async def delete(self, trip_id: str) -> None:
        await self._repo.delete(await self.get(trip_id))
