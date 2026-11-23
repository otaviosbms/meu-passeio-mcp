"""Tools de planejamento — sugestão de bate-voltas e agenda otimizada de um dia.

Textos (descrições, notas, erros): meu_passeio/texts/planning.py
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.places.schemas import PlaceCategory
from meu_passeio.mcp_server.planning import service
from meu_passeio.mcp_server.planning.schemas import DayItinerary, DayStop, DayTripSuggestions
from meu_passeio.shared.schemas import Coordinates, TravelMode, Waypoint
from meu_passeio.texts import planning as T

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


@safe_tool
async def suggest_day_trip_destinations(
    max_drive_hours: Annotated[float, Field(gt=0, le=4, description=T.Params.MAX_DRIVE_HOURS)],
    origin: Annotated[str | None, Field(description=T.Params.ORIGIN)] = None,
    origin_coordinates: Annotated[
        Coordinates | None, Field(description=T.Params.ORIGIN_COORDINATES)
    ] = None,
    interests: Annotated[
        list[PlaceCategory] | None, Field(max_length=5, description=T.Params.INTERESTS)
    ] = None,
    min_rating: Annotated[float, Field(ge=1, le=5, description=T.Params.MIN_RATING)] = 4.3,
    min_reviews: Annotated[int, Field(ge=0, description=T.Params.MIN_REVIEWS)] = 100,
    min_distance_km: Annotated[float, Field(ge=0, description=T.Params.MIN_DISTANCE_KM)] = 20,
    departure_time: Annotated[datetime | None, Field(description=T.Params.DEPARTURE_TIME)] = None,
    limit: Annotated[int, Field(ge=1, le=15, description=T.Params.LIMIT)] = 8,
) -> DayTripSuggestions:
    return await service.suggest_day_trips(
        origin=origin,
        origin_coordinates=origin_coordinates,
        max_drive_hours=max_drive_hours,
        interests=list(interests) if interests else None,
        min_rating=min_rating,
        min_reviews=min_reviews,
        min_distance_km=min_distance_km,
        departure_time=departure_time,
        limit=limit,
    )


@safe_tool
async def optimize_day_itinerary(
    start: Annotated[Waypoint, Field(description=T.Params.START)],
    stops: Annotated[list[DayStop], Field(min_length=1, max_length=10, description=T.Params.STOPS)],
    day: Annotated[date, Field(description=T.Params.DAY)],
    start_time: Annotated[
        str, Field(pattern=r"^\d{1,2}:\d{2}$", description=T.Params.START_TIME)
    ] = "09:00",
    end: Annotated[Waypoint | None, Field(description=T.Params.END)] = None,
    travel_mode: Annotated[TravelMode, Field(description=T.Params.TRAVEL_MODE)] = "driving",
    keep_order: Annotated[bool, Field(description=T.Params.KEEP_ORDER)] = False,
) -> DayItinerary:
    return await service.plan_day(
        start=start,
        stops=stops,
        day=day,
        start_time=start_time,
        end=end,
        mode=travel_mode,
        keep_order=keep_order,
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(
        suggest_day_trip_destinations,
        description=T.Tools.SUGGEST_DAY_TRIP_DESTINATIONS,
        annotations=READ_ONLY,
    )
    mcp.add_tool(
        optimize_day_itinerary,
        description=T.Tools.OPTIMIZE_DAY_ITINERARY,
        annotations=READ_ONLY,
    )
