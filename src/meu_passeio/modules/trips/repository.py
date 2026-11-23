from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meu_passeio.modules.trips.models import Trip


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, trip: Trip) -> Trip:
        self._session.add(trip)
        await self._session.commit()
        await self._session.refresh(trip)
        return trip

    async def get(self, trip_id: str) -> Trip | None:
        return await self._session.get(Trip, trip_id)

    async def list(self, limit: int = 50, offset: int = 0) -> list[Trip]:
        result = await self._session.execute(
            select(Trip).order_by(Trip.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars())

    async def save(self, trip: Trip) -> Trip:
        await self._session.commit()
        await self._session.refresh(trip)
        return trip

    async def delete(self, trip: Trip) -> None:
        await self._session.delete(trip)
        await self._session.commit()
