from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from meu_passeio.api.dependencies import get_trip_service
from meu_passeio.modules.trips.schemas import TripListItem, TripResponse, TripWrite
from meu_passeio.modules.trips.service import TripNotFound, TripService
from meu_passeio.texts.api import Http, Routes

router = APIRouter(prefix="/trips", tags=["trips"])
ServiceDep = Annotated[TripService, Depends(get_trip_service)]


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, Http.TRIP_NOT_FOUND)


@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    description=Routes.CREATE_TRIP,
)
async def create_trip(body: TripWrite, service: ServiceDep):
    return await service.create(body)


@router.get("", response_model=list[TripListItem])
async def list_trips(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await service.list(limit, offset)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: str, service: ServiceDep):
    try:
        return await service.get(trip_id)
    except TripNotFound:
        raise _not_found() from None


@router.put("/{trip_id}", response_model=TripResponse, description=Routes.UPDATE_TRIP)
async def update_trip(trip_id: str, body: TripWrite, service: ServiceDep):
    try:
        return await service.update(trip_id, body)
    except TripNotFound:
        raise _not_found() from None


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: str, service: ServiceDep):
    try:
        await service.delete(trip_id)
    except TripNotFound:
        raise _not_found() from None
