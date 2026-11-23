"""Tools de mapas — distâncias, rotas, tempos de deslocamento e ordenação de paradas.

Textos (descrições, notas, erros): meu_passeio/texts/maps.py
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.common.geo import haversine_km
from meu_passeio.mcp_server.common.http import build_client
from meu_passeio.mcp_server.maps.provider import SOURCE, OsrmProvider
from meu_passeio.shared.schemas import Coordinates, TravelMode
from meu_passeio.texts import maps as T

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
LOCAL = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
_provider: OsrmProvider | None = None


def provider() -> OsrmProvider:
    global _provider
    if _provider is None:
        _provider = OsrmProvider(build_client(timeout=20.0))
    return _provider


class DistanceResult(BaseModel):
    straight_line_km: float
    method: str = "haversine"
    notes: list[str] = Field(default_factory=lambda: [T.Notes.STRAIGHT_LINE])


class RouteResult(BaseModel):
    distance_meters: int
    duration_seconds: int
    travel_mode: TravelMode
    traffic_aware: bool = False
    polyline: str | None = None
    source: str = SOURCE


class TravelTimeMatrix(BaseModel):
    travel_mode: TravelMode
    durations_seconds: list[list[float | None]] = Field(description=T.Fields.DURATIONS)
    distances_meters: list[list[float | None]] | None = None
    traffic_aware: bool = False
    source: str = SOURCE


class OptimizedStops(BaseModel):
    order: list[int] = Field(description=T.Fields.ORDER)
    total_distance_meters: int
    total_duration_seconds: int
    roundtrip: bool
    travel_mode: TravelMode
    source: str = SOURCE


ModeArg = Annotated[TravelMode, Field(description=T.Params.TRAVEL_MODE)]


@safe_tool
async def calculate_distance(origin: Coordinates, destination: Coordinates) -> DistanceResult:
    km = haversine_km(
        origin.latitude, origin.longitude, destination.latitude, destination.longitude
    )
    return DistanceResult(straight_line_km=round(km, 3))


@safe_tool
async def get_route(
    origin: Coordinates,
    destination: Coordinates,
    travel_mode: ModeArg = "driving",
    include_polyline: Annotated[bool, Field(description=T.Params.INCLUDE_POLYLINE)] = False,
) -> RouteResult:
    data = await provider().route(origin, destination, travel_mode, include_polyline)
    return RouteResult(travel_mode=travel_mode, **data)


@safe_tool
async def get_travel_time(
    origins: Annotated[list[Coordinates], Field(min_length=1, max_length=10)],
    destinations: Annotated[list[Coordinates], Field(min_length=1, max_length=10)],
    travel_mode: ModeArg = "driving",
) -> TravelTimeMatrix:
    data = await provider().table(origins, destinations, travel_mode)
    return TravelTimeMatrix(
        travel_mode=travel_mode,
        durations_seconds=data["durations"] or [],
        distances_meters=data["distances"],
    )


@safe_tool
async def optimize_stops(
    stops: Annotated[
        list[Coordinates], Field(min_length=2, max_length=12, description=T.Params.STOPS)
    ],
    travel_mode: ModeArg = "driving",
    roundtrip: Annotated[bool, Field(description=T.Params.ROUNDTRIP)] = False,
) -> OptimizedStops:
    data = await provider().trip(stops, travel_mode, roundtrip)
    return OptimizedStops(
        order=data["order"],
        total_distance_meters=data["distance_meters"],
        total_duration_seconds=data["duration_seconds"],
        roundtrip=roundtrip,
        travel_mode=travel_mode,
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(calculate_distance, description=T.Tools.CALCULATE_DISTANCE, annotations=LOCAL)
    mcp.add_tool(get_route, description=T.Tools.GET_ROUTE, annotations=READ_ONLY)
    mcp.add_tool(get_travel_time, description=T.Tools.GET_TRAVEL_TIME, annotations=READ_ONLY)
    mcp.add_tool(optimize_stops, description=T.Tools.OPTIMIZE_STOPS, annotations=READ_ONLY)
