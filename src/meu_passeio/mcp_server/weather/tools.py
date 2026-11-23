"""Tools de clima — previsão do tempo para planejamento de atividades.

Textos (descrições, notas, erros): meu_passeio/texts/weather.py
"""

from __future__ import annotations

import datetime as dt
from datetime import date, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.common.http import build_client
from meu_passeio.mcp_server.weather import climate
from meu_passeio.mcp_server.weather.provider import MAX_FORECAST_DAYS, SOURCE, OpenMeteoProvider
from meu_passeio.mcp_server.weather.sun import sun_day
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


def _check_window(start: date, end: date) -> None:
    if end < start:
        raise ValueError(T.Errors.END_BEFORE_START)
    if (end - start).days >= climate.MAX_WINDOW_DAYS:
        raise ValueError(T.Errors.RANGE_TOO_LONG)


@safe_tool
async def get_climate_normals(
    start_date: Annotated[date, Field(description=T.Params.CLIMATE_START)],
    end_date: Annotated[date, Field(description=T.Params.CLIMATE_END)],
    location: LocationArg = None,
    coordinates: Coordinates | None = None,
    years: Annotated[int, Field(ge=3, le=30, description=T.Params.CLIMATE_YEARS)] = 10,
) -> climate.ClimateNormals:
    _check_window(start_date, end_date)
    coords, resolved = await _resolve(location, coordinates)
    windows = climate.year_windows(start_date, end_date, years, date.today())
    if not windows:
        raise ValueError(T.Errors.NO_HISTORY)
    daily = await provider().archive_daily(coords, windows[0][0], windows[-1][1])
    stats = climate.summarize(daily, windows)
    return climate.ClimateNormals(
        location=coords,
        resolved_location=resolved,
        period=f"{start_date:%d/%m} a {end_date:%d/%m}",
        years=f"{windows[0][0].year}–{windows[-1][0].year}",
        notes=[T.Notes.CLIMATE_METHOD.format(count=len(windows))],
        **stats,  # type: ignore[arg-type]
    )


class SunTimes(BaseModel):
    date: dt.date
    sunrise: str | None
    sunset: str | None
    solar_noon: str
    civil_dawn: str | None = Field(description=T.Fields.CIVIL_TWILIGHT)
    civil_dusk: str | None = Field(description=T.Fields.CIVIL_TWILIGHT)
    golden_hour_morning: str | None = Field(description=T.Fields.GOLDEN_HOUR)
    golden_hour_evening: str | None = Field(description=T.Fields.GOLDEN_HOUR)
    day_length: str | None


class SunTimesResult(BaseModel):
    location: Coordinates
    resolved_location: str | None = None
    timezone: str
    days: list[SunTimes]
    source: str = T.SUN_SOURCE
    notes: list[str] = Field(default_factory=list)


def _hm(value: dt.datetime | None) -> str | None:
    return value.strftime("%H:%M") if value else None


@safe_tool
async def get_sun_times(
    start_date: Annotated[date, Field(description=T.Params.START_DATE)],
    end_date: Annotated[date | None, Field(description=T.Params.SUN_END_DATE)] = None,
    location: LocationArg = None,
    coordinates: Coordinates | None = None,
) -> SunTimesResult:
    end_date = end_date or start_date
    _check_window(start_date, end_date)
    coords, resolved = await _resolve(location, coordinates)
    tz_name = await provider().timezone_name(coords)
    tz = ZoneInfo(tz_name)
    days = []
    for offset in range((end_date - start_date).days + 1):
        info = sun_day(start_date + timedelta(days=offset), coords.latitude, coords.longitude, tz)
        length = info.day_length_minutes
        days.append(
            SunTimes(
                date=info.date,
                sunrise=_hm(info.sunrise),
                sunset=_hm(info.sunset),
                solar_noon=_hm(info.solar_noon) or "",
                civil_dawn=_hm(info.civil_dawn),
                civil_dusk=_hm(info.civil_dusk),
                golden_hour_morning=(
                    f"{_hm(info.sunrise)}–{_hm(info.golden_hour_morning_end)}"
                    if info.sunrise and info.golden_hour_morning_end
                    else None
                ),
                golden_hour_evening=(
                    f"{_hm(info.golden_hour_evening_start)}–{_hm(info.sunset)}"
                    if info.sunset and info.golden_hour_evening_start
                    else None
                ),
                day_length=f"{length // 60}h{length % 60:02d}" if length is not None else None,
            )
        )
    return SunTimesResult(
        location=coords,
        resolved_location=resolved,
        timezone=tz_name,
        days=days,
        notes=[T.Notes.SUN_METHOD],
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(get_forecast, description=T.Tools.GET_FORECAST, annotations=READ_ONLY)
    mcp.add_tool(
        get_weather_by_date, description=T.Tools.GET_WEATHER_BY_DATE, annotations=READ_ONLY
    )
    mcp.add_tool(
        get_climate_normals, description=T.Tools.GET_CLIMATE_NORMALS, annotations=READ_ONLY
    )
    mcp.add_tool(get_sun_times, description=T.Tools.GET_SUN_TIMES, annotations=READ_ONLY)
