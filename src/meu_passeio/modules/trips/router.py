from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from meu_passeio.api.dependencies import get_trip_service
from meu_passeio.modules.trips.schemas import (
    ClarifyTripRequest,
    CreateTripRequest,
    ReviseTripRequest,
    TripListItem,
    TripResponse,
)
from meu_passeio.modules.trips.service import InvalidTripState, TripNotFound, TripService

router = APIRouter(prefix="/trips", tags=["trips"])
ServiceDep = Annotated[TripService, Depends(get_trip_service)]


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Viagem não encontrada.")


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(body: CreateTripRequest, service: ServiceDep):
    """Planeja uma viagem a partir de uma descrição em linguagem natural."""
    return await service.create(body.request)


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


@router.post("/{trip_id}/clarify", response_model=TripResponse)
async def clarify_trip(trip_id: str, body: ClarifyTripRequest, service: ServiceDep):
    """Responde às perguntas do planner e reexecuta o planejamento."""
    try:
        return await service.clarify(trip_id, body.answer)
    except TripNotFound:
        raise _not_found() from None
    except InvalidTripState as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None


@router.post("/{trip_id}/revise", response_model=TripResponse)
async def revise_trip(trip_id: str, body: ReviseTripRequest, service: ServiceDep):
    """Edição conversacional: altera só o necessário e preserva o restante do roteiro."""
    try:
        return await service.revise(trip_id, body.instruction)
    except TripNotFound:
        raise _not_found() from None
    except InvalidTripState as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: str, service: ServiceDep):
    try:
        await service.delete(trip_id)
    except TripNotFound:
        raise _not_found() from None
