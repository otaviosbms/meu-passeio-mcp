"""Médias climáticas de um período do ano, a partir do histórico diário do Open-Meteo.

Para datas além do horizonte da previsão, mostra como o tempo costuma ser naquele período:
média de N anos das mesmas datas (temperaturas, chuva, chance de dia chuvoso, sol).
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field

from meu_passeio.mcp_server.weather.provider import SOURCE
from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import weather as T

RAINY_DAY_MM = 1.0
MAX_WINDOW_DAYS = 31


class ClimateNormals(BaseModel):
    location: Coordinates
    resolved_location: str | None = None
    period: str = Field(description=T.Fields.CLIMATE_PERIOD)
    years: str = Field(description=T.Fields.CLIMATE_YEARS)
    days_sampled: int
    avg_temperature_max_c: float | None = None
    avg_temperature_min_c: float | None = None
    highest_temperature_c: float | None = None
    lowest_temperature_c: float | None = None
    avg_precipitation_mm_per_day: float | None = None
    rainy_day_probability_pct: float | None = Field(default=None, description=T.Fields.RAINY_DAYS)
    avg_sunshine_hours: float | None = None
    avg_wind_speed_max_kmh: float | None = None
    source: str = SOURCE
    notes: list[str] = Field(default_factory=list)


def _same_day(year: int, ref: date) -> date:
    try:
        return ref.replace(year=year)
    except ValueError:  # 29/02 em ano não bissexto
        return date(year, 2, 28)


def year_windows(start: date, end: date, years: int, today: date) -> list[tuple[date, date]]:
    """Mesmas datas (dia/mês) em cada um dos ``years`` anos completos anteriores."""
    length = (end - start).days
    last_year = today.year - 1
    windows = []
    for year in range(last_year - years + 1, last_year + 1):
        window_start = _same_day(year, start)
        window_end = window_start + timedelta(days=length)
        if window_end >= today - timedelta(days=7):  # o histórico tem alguns dias de atraso
            continue
        windows.append((window_start, window_end))
    return windows


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


def summarize(
    daily: dict[str, list[Any]], windows: list[tuple[date, date]]
) -> dict[str, float | int | None]:
    dates = [date.fromisoformat(d) for d in daily.get("time", [])]
    selected = [i for i, d in enumerate(dates) if any(start <= d <= end for start, end in windows)]

    def column(name: str) -> list[float]:
        values = daily.get(name) or []
        return [values[i] for i in selected if i < len(values) and values[i] is not None]

    tmax, tmin = column("temperature_2m_max"), column("temperature_2m_min")
    rain, sun = column("precipitation_sum"), column("sunshine_duration")
    wind = column("wind_speed_10m_max")
    mean = statistics.fmean
    return {
        "days_sampled": len(selected),
        "avg_temperature_max_c": _round(mean(tmax)) if tmax else None,
        "avg_temperature_min_c": _round(mean(tmin)) if tmin else None,
        "highest_temperature_c": max(tmax) if tmax else None,
        "lowest_temperature_c": min(tmin) if tmin else None,
        "avg_precipitation_mm_per_day": _round(mean(rain)) if rain else None,
        "rainy_day_probability_pct": (
            _round(100 * sum(r >= RAINY_DAY_MM for r in rain) / len(rain), 0) if rain else None
        ),
        "avg_sunshine_hours": _round(mean(sun) / 3600) if sun else None,
        "avg_wind_speed_max_kmh": _round(mean(wind)) if wind else None,
    }
