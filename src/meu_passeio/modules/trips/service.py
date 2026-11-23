"""Regras de negócio de viagens: persistência de roteiros montados pelo cliente."""

from __future__ import annotations

from meu_passeio.modules.trips.models import Trip
from meu_passeio.modules.trips.repository import TripRepository
from meu_passeio.modules.trips.schemas import TripWrite


class TripNotFound(LookupError):
    pass


class TripService:
    def __init__(self, repository: TripRepository) -> None:
        self._repo = repository

    async def create(self, data: TripWrite) -> Trip:
        return await self._repo.add(
            Trip(title=data.title or data.plan.title, plan=data.plan.model_dump(mode="json"))
        )

    async def update(self, trip_id: str, data: TripWrite) -> Trip:
        trip = await self.get(trip_id)
        trip.title = data.title or data.plan.title
        trip.plan = data.plan.model_dump(mode="json")
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
