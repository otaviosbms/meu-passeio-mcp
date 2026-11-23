"""Weather MCP Server — previsão do tempo para planejamento de atividades.

Execução (stdio):  python -m meu_passeio.mcp_servers.weather
"""

from __future__ import annotations

import datetime as dt
from datetime import date, timedelta
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.core.logging import configure_logging
from meu_passeio.mcp_servers.common.errors import safe_tool
from meu_passeio.mcp_servers.common.http import build_client
from meu_passeio.mcp_servers.weather.provider import MAX_FORECAST_DAYS, SOURCE, OpenMeteoProvider
from meu_passeio.shared.schemas import Coordinates

mcp = MCPServer(
    name="meu-passeio-weather",
    instructions=(
        f"Previsão diária (Open-Meteo), disponível até {MAX_FORECAST_DAYS} dias à frente. "
        "Para datas mais distantes, a previsão não existe: comunique a incerteza."
    ),
)
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


LocationArg = Annotated[
    str | None,
    Field(description="Cidade em texto, ex.: 'Campos do Jordão, SP'. Ou use coordinates."),
]


async def _resolve(location: str | None, coordinates: Coordinates | None):
    if coordinates is not None:
        return coordinates, None
    if not location:
        raise ValueError("Informe 'location' ou 'coordinates'.")
    return await provider().geocode(location)


async def _forecast(
    location: str | None, coordinates: Coordinates | None, start: date, end: date
) -> ForecastResult:
    if end < start:
        raise ValueError("end_date deve ser >= start_date.")
    if (end - start).days > 30:
        raise ValueError("Intervalo máximo de 31 dias.")
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
            notes.append("Previsões com mais de 7 dias de antecedência têm baixa confiabilidade.")

    covered = {d.date for d in days}
    unavailable = [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if start + timedelta(days=i) not in covered
    ]
    if unavailable:
        notes.append(
            f"Sem previsão para {len(unavailable)} data(s): fora do horizonte de "
            f"{MAX_FORECAST_DAYS} dias ou no passado. Planeje com alternativas indoor."
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


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def get_forecast(
    start_date: Annotated[date, Field(description="Data inicial (YYYY-MM-DD)")],
    end_date: Annotated[date, Field(description="Data final (YYYY-MM-DD)")],
    location: LocationArg = None,
    coordinates: Coordinates | None = None,
) -> ForecastResult:
    """Previsão diária (condição, temperaturas, chuva, vento, UV) para um intervalo de datas."""
    return await _forecast(location, coordinates, start_date, end_date)


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def get_weather_by_date(
    target_date: Annotated[date, Field(description="Data (YYYY-MM-DD)")],
    location: LocationArg = None,
    coordinates: Coordinates | None = None,
) -> ForecastResult:
    """Previsão para uma data específica, se estiver dentro do horizonte de previsão."""
    return await _forecast(location, coordinates, target_date, target_date)


def main() -> None:
    configure_logging()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
