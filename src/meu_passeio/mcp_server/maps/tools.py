"""Tools de mapas — Google Routes (trânsito e pedágios) com OSRM como alternativa.

A escolha do provider e o fallback ficam em ``maps/service.py``.
Textos (descrições, notas, erros): meu_passeio/texts/maps.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.common.geo import haversine_km
from meu_passeio.mcp_server.maps import service
from meu_passeio.mcp_server.maps.schemas import (
    DistanceResult,
    OptimizedStops,
    RouteOptions,
    TollEstimate,
    TravelTimeMatrix,
)
from meu_passeio.shared.schemas import Coordinates, TravelMode, Waypoint
from meu_passeio.texts import maps as T

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
LOCAL = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

ModeArg = Annotated[TravelMode, Field(description=T.Params.TRAVEL_MODE)]
DepartureArg = Annotated[datetime | None, Field(description=T.Params.DEPARTURE_TIME)]


@safe_tool
async def calculate_distance(origin: Coordinates, destination: Coordinates) -> DistanceResult:
    km = haversine_km(
        origin.latitude, origin.longitude, destination.latitude, destination.longitude
    )
    return DistanceResult(straight_line_km=round(km, 3))


@safe_tool
async def get_route(
    origin: Annotated[Waypoint, Field(description=T.Params.WAYPOINT)],
    destination: Annotated[Waypoint, Field(description=T.Params.WAYPOINT)],
    travel_mode: ModeArg = "driving",
    departure_time: DepartureArg = None,
    alternatives: Annotated[bool, Field(description=T.Params.ALTERNATIVES)] = False,
    avoid_tolls: Annotated[bool, Field(description=T.Params.AVOID_TOLLS)] = False,
    avoid_highways: Annotated[bool, Field(description=T.Params.AVOID_HIGHWAYS)] = False,
    include_polyline: Annotated[bool, Field(description=T.Params.INCLUDE_POLYLINE)] = False,
) -> RouteOptions:
    return await service.route(
        origin,
        destination,
        mode=travel_mode,
        departure_time=departure_time,
        alternatives=alternatives,
        avoid_tolls=avoid_tolls,
        avoid_highways=avoid_highways,
        include_polyline=include_polyline,
    )


@safe_tool
async def estimate_toll_costs(
    origin: Annotated[Waypoint, Field(description=T.Params.WAYPOINT)],
    destination: Annotated[Waypoint, Field(description=T.Params.WAYPOINT)],
    round_trip: Annotated[bool, Field(description=T.Params.TOLL_ROUND_TRIP)] = True,
    departure_time: DepartureArg = None,
) -> TollEstimate:
    return await service.tolls(
        origin, destination, round_trip=round_trip, departure_time=departure_time
    )


@safe_tool
async def get_travel_time(
    origins: Annotated[list[Waypoint], Field(min_length=1, max_length=10)],
    destinations: Annotated[list[Waypoint], Field(min_length=1, max_length=10)],
    travel_mode: ModeArg = "driving",
    departure_time: DepartureArg = None,
) -> TravelTimeMatrix:
    return await service.matrix(
        origins, destinations, mode=travel_mode, departure_time=departure_time
    )


@safe_tool
async def optimize_stops(
    stops: Annotated[
        list[Waypoint], Field(min_length=2, max_length=12, description=T.Params.STOPS)
    ],
    travel_mode: ModeArg = "driving",
    roundtrip: Annotated[bool, Field(description=T.Params.ROUNDTRIP)] = False,
    departure_time: DepartureArg = None,
) -> OptimizedStops:
    return await service.optimize(
        stops, mode=travel_mode, roundtrip=roundtrip, departure_time=departure_time
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(calculate_distance, description=T.Tools.CALCULATE_DISTANCE, annotations=LOCAL)
    mcp.add_tool(get_route, description=T.Tools.GET_ROUTE, annotations=READ_ONLY)
    mcp.add_tool(
        estimate_toll_costs, description=T.Tools.ESTIMATE_TOLL_COSTS, annotations=READ_ONLY
    )
    mcp.add_tool(get_travel_time, description=T.Tools.GET_TRAVEL_TIME, annotations=READ_ONLY)
    mcp.add_tool(optimize_stops, description=T.Tools.OPTIMIZE_STOPS, annotations=READ_ONLY)
