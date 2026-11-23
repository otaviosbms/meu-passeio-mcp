"""Tools de roteiros — salvar, listar, abrir e atualizar viagens no banco do projeto.

Usam o mesmo banco e as mesmas regras da API (``modules/trips``): um roteiro salvo pelo
Claude aparece em ``GET /trips`` e vice-versa.
Textos (descrições, erros): meu_passeio/texts/trips.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.core.config import get_settings
from meu_passeio.db.session import Database
from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.common.http import ProviderError
from meu_passeio.modules.trips.repository import TripRepository
from meu_passeio.modules.trips.schemas import TripListItem, TripResponse, TripWrite
from meu_passeio.modules.trips.service import TripNotFound, TripService
from meu_passeio.shared.schemas import TripPlan
from meu_passeio.texts import trips as T

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)
OVERWRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False
)

_db: Database | None = None
_ready = asyncio.Lock()


async def database() -> Database:
    """Abre o banco configurado (MEU_PASSEIO_DATABASE_URL) e cria as tabelas na 1ª vez."""
    global _db
    async with _ready:
        if _db is None:
            db = Database(get_settings().database_url)
            await db.create_all()
            _db = db
    return _db


async def _run(action):  # noqa: ANN001, ANN202 — helper interno
    db = await database()
    async with db.sessionmaker() as session:
        try:
            return await action(TripService(TripRepository(session)))
        except TripNotFound as exc:
            raise ProviderError(T.Errors.NOT_FOUND.format(trip_id=exc)) from exc


class SavedTrip(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    message: str


class TripList(BaseModel):
    trips: list[TripListItem]
    count: int


TitleArg = Annotated[str | None, Field(max_length=255, description=T.Params.TITLE)]
TripIdArg = Annotated[str, Field(description=T.Params.TRIP_ID)]


@safe_tool
async def save_trip(
    plan: Annotated[TripPlan, Field(description=T.Params.PLAN)],
    title: TitleArg = None,
) -> SavedTrip:
    trip = await _run(lambda s: s.create(TripWrite(title=title, plan=plan)))
    return SavedTrip(
        id=trip.id,
        title=trip.title,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
        message=T.Messages.SAVED.format(trip_id=trip.id),
    )


@safe_tool
async def list_trips(
    limit: Annotated[int, Field(ge=1, le=100, description=T.Params.LIMIT)] = 20,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> TripList:
    trips = await _run(lambda s: s.list(limit, offset))
    items = [TripListItem.model_validate(t) for t in trips]
    return TripList(trips=items, count=len(items))


@safe_tool
async def get_trip(trip_id: TripIdArg) -> TripResponse:
    trip = await _run(lambda s: s.get(trip_id))
    return TripResponse.model_validate(trip)


@safe_tool
async def update_trip(
    trip_id: TripIdArg,
    plan: Annotated[TripPlan, Field(description=T.Params.PLAN_UPDATE)],
    title: TitleArg = None,
) -> SavedTrip:
    trip = await _run(lambda s: s.update(trip_id, TripWrite(title=title, plan=plan)))
    return SavedTrip(
        id=trip.id,
        title=trip.title,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
        message=T.Messages.UPDATED.format(trip_id=trip.id),
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(save_trip, description=T.Tools.SAVE_TRIP, annotations=WRITE)
    mcp.add_tool(list_trips, description=T.Tools.LIST_TRIPS, annotations=READ)
    mcp.add_tool(get_trip, description=T.Tools.GET_TRIP, annotations=READ)
    mcp.add_tool(update_trip, description=T.Tools.UPDATE_TRIP, annotations=OVERWRITE)
