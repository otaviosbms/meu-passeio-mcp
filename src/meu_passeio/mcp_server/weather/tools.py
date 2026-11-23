"""Tools de clima — previsão do tempo para planejamento de atividades.

Textos (descrições, notas, erros): meu_passeio/texts/weather.py
"""

from __future__ import annotations

import datetime as dt
from datetime import date, timedelta
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.common.http import build_client
from meu_passeio.mcp_server.weather.provider import MAX_FORECAST_DAYS, SOURCE, OpenMeteoProvider
from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import weather as T

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
_provider: OpenMeteoProvider | None = None


def provider() -> OpenMeteoProvider:
    global _provider
    if _provider is None:
        _provider = OpenMeteoProvider(build_client(timeout=15.0))
    return _provider


class DailyWeather(BaseModel):
    date: dt.date
    condition: str | None
    weather_code: int | None
    temperature_max_c: float | None
    temperature_min_c: float | None
    precipitation_mm: float | None
    precipitation_probability_pct: float | None
    wind_speed_max_kmh: float | None
    uv_index_max: float | None


class ForecastResult(BaseModel):
    location: Coordinates
    resolved_location: str | None = None
    timezone: str | None = None
    available: bool
    days: list[DailyWeather] = Field(default_factory=list)
    unavailable_dates: list[date] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    source: str = SOURCE


LocationArg = Annotated[str | None, Field(description=T.Params.LOCATION)]


async def _resolve(location: str | None, coordinates: Coordinates | None):
    if coordinates is not None:
        return coordinates, None
    if not location:
        raise ValueError(T.Errors.MISSING_LOCATION)
    return await provider().geocode(location)


async def _forecast(
    location: str | None, coordinates: Coordinates | None, start: date, end: date
) -> ForecastResult:
    if end < start:
        raise ValueError(T.Errors.END_BEFORE_START)
    if (end - start).days > 30:
        raise ValueError(T.Errors.RANGE_TOO_LONG)
    coords, resolved = await _resolve(location, coordinates)

    today = date.today()
    horizon = today + timedelta(days=MAX_FORECAST_DAYS - 1)
    window_start, window_end = max(start, today), min(end, horizon)

    notes: list[str] = []
    days: list[DailyWeather] = []
    timezone = None
    if window_start <= window_end:
        raw, timezone = await provider().daily_forecast(coords, window_start, window_end)
        days = [DailyWeather(**d) for d in raw]
        if (window_start - today).days > 7:
            notes.append(T.Notes.LOW_CONFIDENCE)

    covered = {d.date for d in days}
    unavailable = [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if start + timedelta(days=i) not in covered
    ]
    if unavailable:
        notes.append(
            T.Notes.UNAVAILABLE_DATES.format(count=len(unavailable), max_days=MAX_FORECAST_DAYS)
        )
    return ForecastResult(
        location=coords,
        resolved_location=resolved,
        timezone=timezone,
        available=bool(days),
        days=days,
        unavailable_dates=unavailable,
        notes=notes,
    )


@safe_tool
async def get_forecast(
    start_date: Annotated[date, Field(description=T.Params.START_DATE)],
    end_date: Annotated[date, Field(description=T.Params.END_DATE)],
    location: LocationArg = None,
    coordinates: Coordinates | None = None,
) -> ForecastResult:
    return await _forecast(location, coordinates, start_date, end_date)


@safe_tool
async def get_weather_by_date(
    target_date: Annotated[date, Field(description=T.Params.TARGET_DATE)],
    location: LocationArg = None,
    coordinates: Coordinates | None = None,
) -> ForecastResult:
    return await _forecast(location, coordinates, target_date, target_date)


def register(mcp: MCPServer) -> None:
    mcp.add_tool(get_forecast, description=T.Tools.GET_FORECAST, annotations=READ_ONLY)
    mcp.add_tool(
        get_weather_by_date, description=T.Tools.GET_WEATHER_BY_DATE, annotations=READ_ONLY
    )
