"""Maps MCP Server — distâncias, rotas, tempos de deslocamento e ordenação de paradas.

Execução (stdio):  python -m meu_passeio.mcp_servers.maps
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.core.logging import configure_logging
from meu_passeio.mcp_servers.common.errors import safe_tool
from meu_passeio.mcp_servers.common.geo import haversine_km
from meu_passeio.mcp_servers.common.http import build_client
from meu_passeio.mcp_servers.maps.provider import SOURCE, OsrmProvider
from meu_passeio.shared.schemas import Coordinates, TravelMode

mcp = MCPServer(
    name="meu-passeio-maps",
    instructions=(
        "Cálculo de distâncias e rotas (OSRM/OpenStreetMap). Durações NÃO consideram trânsito "
        "em tempo real."
    ),
)
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
_provider: OsrmProvider | None = None


def provider() -> OsrmProvider:
    global _provider
    if _provider is None:
        _provider = OsrmProvider(build_client(timeout=20.0))
    return _provider


class DistanceResult(BaseModel):
    straight_line_km: float
    method: str = "haversine"
    notes: list[str] = Field(
        default_factory=lambda: ["Distância em linha reta; use get_route para distância viária."]
    )


class RouteResult(BaseModel):
    distance_meters: int
    duration_seconds: int
    travel_mode: TravelMode
    traffic_aware: bool = False
    polyline: str | None = None
    source: str = SOURCE


class TravelTimeMatrix(BaseModel):
    travel_mode: TravelMode
    durations_seconds: list[list[float | None]] = Field(
        description="durations_seconds[i][j] = origem i -> destino j"
    )
    distances_meters: list[list[float | None]] | None = None
    traffic_aware: bool = False
    source: str = SOURCE


class OptimizedStops(BaseModel):
    order: list[int] = Field(description="Índices das paradas de entrada na ordem sugerida")
    total_distance_meters: int
    total_duration_seconds: int
    roundtrip: bool
    travel_mode: TravelMode
    source: str = SOURCE


ModeArg = Annotated[TravelMode, Field(description="Meio de transporte")]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
@safe_tool
async def calculate_distance(origin: Coordinates, destination: Coordinates) -> DistanceResult:
    """Calcula a distância em linha reta (km) entre dois pontos. Rápido e sem provedor externo."""
    km = haversine_km(
        origin.latitude, origin.longitude, destination.latitude, destination.longitude
    )
    return DistanceResult(straight_line_km=round(km, 3))


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def get_route(
    origin: Coordinates,
    destination: Coordinates,
    travel_mode: ModeArg = "driving",
    include_polyline: Annotated[bool, Field(description="Incluir polyline simplificada")] = False,
) -> RouteResult:
    """Obtém a rota viária entre dois pontos: distância (m) e duração estimada (s)."""
    data = await provider().route(origin, destination, travel_mode, include_polyline)
    return RouteResult(travel_mode=travel_mode, **data)


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def get_travel_time(
    origins: Annotated[list[Coordinates], Field(min_length=1, max_length=10)],
    destinations: Annotated[list[Coordinates], Field(min_length=1, max_length=10)],
    travel_mode: ModeArg = "driving",
) -> TravelTimeMatrix:
    """Estima tempos de deslocamento entre vários locais (matriz origens x destinos)."""
    data = await provider().table(origins, destinations, travel_mode)
    return TravelTimeMatrix(
        travel_mode=travel_mode,
        durations_seconds=data["durations"] or [],
        distances_meters=data["distances"],
    )


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def optimize_stops(
    stops: Annotated[
        list[Coordinates],
        Field(min_length=2, max_length=12, description="Paradas; a primeira é o ponto de partida"),
    ],
    travel_mode: ModeArg = "driving",
    roundtrip: Annotated[bool, Field(description="Voltar ao ponto inicial no fim")] = False,
) -> OptimizedStops:
    """Sugere uma ordem eficiente para visitar várias paradas (problema do caixeiro viajante)."""
    data = await provider().trip(stops, travel_mode, roundtrip)
    return OptimizedStops(
        order=data["order"],
        total_distance_meters=data["distance_meters"],
        total_duration_seconds=data["duration_seconds"],
        roundtrip=roundtrip,
        travel_mode=travel_mode,
    )


def main() -> None:
    configure_logging()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
