"""Provider de clima baseado em Open-Meteo (sem API key)."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx

from meu_passeio.mcp_servers.common.http import ProviderError, get_json
from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import weather as T
from meu_passeio.texts.common import ProviderErrors

FORECAST_URL = os.getenv("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
GEOCODING_URL = os.getenv(
    "OPEN_METEO_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search"
)
SOURCE = "open-meteo"
MAX_FORECAST_DAYS = 16

_DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "uv_index_max",
]


class OpenMeteoProvider:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def geocode(self, location: str) -> tuple[Coordinates, str]:
        # Open-Meteo geocoding funciona melhor só com o nome da cidade.
        name = location.split(",")[0].strip()
        data = await get_json(
            self._client,
            GEOCODING_URL,
            params={"name": name, "count": 5, "language": "pt", "format": "json"},
            provider=SOURCE,
        )
        results: list[dict[str, Any]] = data.get("results") or []
        if not results:
            raise ProviderError(ProviderErrors.LOCATION_NOT_FOUND.format(location=location))
        lowered = location.lower()
        best = next(
            (r for r in results if (r.get("admin1") or "").lower() in lowered and r.get("admin1")),
            results[0],
        )
        label = ", ".join(
            p for p in [best.get("name"), best.get("admin1"), best.get("country")] if p
        )
        return Coordinates(latitude=best["latitude"], longitude=best["longitude"]), label

    async def daily_forecast(
        self, coords: Coordinates, start: date, end: date
    ) -> tuple[list[dict[str, Any]], str | None]:
        data = await get_json(
            self._client,
            FORECAST_URL,
            params={
                "latitude": coords.latitude,
                "longitude": coords.longitude,
                "daily": ",".join(_DAILY_FIELDS),
                "timezone": "auto",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            provider=SOURCE,
        )
        daily = data.get("daily") or {}
        days: list[dict[str, Any]] = []
        for i, day in enumerate(daily.get("time", [])):
            code = daily["weather_code"][i]
            days.append(
                {
                    "date": day,
                    "condition": T.CONDITIONS.get(code, T.UNKNOWN_CONDITION)
                    if code is not None
                    else None,
                    "weather_code": code,
                    "temperature_max_c": daily["temperature_2m_max"][i],
                    "temperature_min_c": daily["temperature_2m_min"][i],
                    "precipitation_mm": daily["precipitation_sum"][i],
                    "precipitation_probability_pct": daily["precipitation_probability_max"][i],
                    "wind_speed_max_kmh": daily["wind_speed_10m_max"][i],
                    "uv_index_max": daily["uv_index_max"][i],
                }
            )
        return days, data.get("timezone")
