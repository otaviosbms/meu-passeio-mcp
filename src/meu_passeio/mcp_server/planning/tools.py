"""Tools de planejamento — bate-voltas, agenda otimizada de um dia e feriados.

Textos (descrições, notas, erros): meu_passeio/texts/planning.py
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.places.schemas import PlaceCategory
from meu_passeio.mcp_server.planning import service
from meu_passeio.mcp_server.planning.holidays import holidays_between, long_weekend
from meu_passeio.mcp_server.planning.schemas import DayItinerary, DayStop, DayTripSuggestions
from meu_passeio.shared.schemas import Coordinates, TravelMode, Waypoint
from meu_passeio.texts import planning as T

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
LOCAL = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
MAX_HOLIDAY_RANGE_DAYS = 366


class HolidayItem(BaseModel):
    date: date
    weekday: str
    name: str
    kind: str = Field(description=T.Fields.HOLIDAY_KIND)
    long_weekend: str | None = Field(default=None, description=T.Fields.LONG_WEEKEND)


class HolidaysResult(BaseModel):
    start_date: date
    end_date: date
    holidays: list[HolidayItem]
    notes: list[str] = Field(default_factory=list)


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


@safe_tool
async def get_holidays(
    start_date: Annotated[date, Field(description=T.Params.HOLIDAYS_START)],
    end_date: Annotated[date | None, Field(description=T.Params.HOLIDAYS_END)] = None,
) -> HolidaysResult:
    end_date = end_date or date(start_date.year, 12, 31)
    if end_date < start_date:
        raise ValueError(T.Errors.END_BEFORE_START)
    if (end_date - start_date).days > MAX_HOLIDAY_RANGE_DAYS:
        raise ValueError(T.Errors.HOLIDAY_RANGE_TOO_LONG)
    items = [
        HolidayItem(
            date=h.date,
            weekday=T.WEEKDAYS[h.date.weekday()],
            name=h.name,
            kind=T.HOLIDAY_KINDS[h.kind],
            long_weekend=long_weekend(h),
        )
        for h in holidays_between(start_date, end_date)
    ]
    return HolidaysResult(
        start_date=start_date, end_date=end_date, holidays=items, notes=[T.Notes.HOLIDAYS_SCOPE]
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(get_holidays, description=T.Tools.GET_HOLIDAYS, annotations=LOCAL)
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
