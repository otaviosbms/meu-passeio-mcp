"""Places MCP Server — descoberta e detalhes de locais (OpenStreetMap).

Execução (stdio):  python -m meu_passeio.mcp_servers.places
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from meu_passeio.core.logging import configure_logging
from meu_passeio.mcp_servers.common.errors import safe_tool
from meu_passeio.mcp_servers.common.http import build_client
from meu_passeio.mcp_servers.places.provider import OsmPlacesProvider
from meu_passeio.mcp_servers.places.schemas import (
    FoodCategory,
    PlaceCategory,
    PlaceDetails,
    PlaceSearchResult,
)
from meu_passeio.shared.schemas import Coordinates

mcp = MCPServer(
    name="meu-passeio-places",
    instructions=(
        "Descoberta de lugares (atrações, natureza, cultura, alimentação) via OpenStreetMap. "
        "Avaliações não estão disponíveis neste provedor (rating=null)."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
_provider: OsmPlacesProvider | None = None


def provider() -> OsmPlacesProvider:
    global _provider
    if _provider is None:
        _provider = OsmPlacesProvider(build_client(timeout=30.0))
    return _provider


LocationArg = Annotated[
    str | None,
    Field(
        description="Cidade/região em texto, ex.: 'Curitiba, PR, Brasil'. Use isto OU coordinates."
    ),
]
CoordinatesArg = Annotated[
    Coordinates | None, Field(description="Centro da busca. Use isto OU location.")
]
RadiusArg = Annotated[float, Field(ge=0.5, le=100, description="Raio de busca em km")]
LimitArg = Annotated[int, Field(ge=1, le=30, description="Máximo de resultados")]


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def search_places(
    categories: Annotated[
        list[PlaceCategory] | None,
        Field(description="Categorias de lugar. Se omitido, usa 'query' como busca textual."),
    ] = None,
    query: Annotated[
        str | None,
        Field(
            description="Texto livre (busca por nome/termo) ou filtro de nome quando há categorias"
        ),
    ] = None,
    location: LocationArg = None,
    coordinates: CoordinatesArg = None,
    radius_km: RadiusArg = 10,
    limit: LimitArg = 10,
) -> PlaceSearchResult:
    """Busca lugares por categoria e/ou texto em torno de uma cidade ou coordenada.

    Retorna nome, categoria, endereço, coordenadas, distância do centro e horário de
    funcionamento (texto bruto do OSM, quando existir). Resultados ordenados por distância.
    """
    p = provider()
    center, resolved = await p.resolve_center(location, coordinates)
    notes: list[str] = []
    if categories:
        places, total = await p.search_by_categories(
            center=center,
            categories=list(categories),
            radius_km=radius_km,
            limit=limit,
            name_contains=query,
        )
    elif query:
        places, total = await p.search_by_text(
            query=query, center=center, radius_km=radius_km, limit=limit
        )
    else:
        raise ValueError("Informe 'categories' e/ou 'query'.")
    if not places:
        notes.append("Nenhum lugar encontrado; tente aumentar o raio ou mudar as categorias.")
    return PlaceSearchResult(
        center=center,
        resolved_location=resolved,
        radius_km=radius_km,
        places=places,
        total_found=total,
        notes=notes,
    )


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def search_restaurants(
    location: LocationArg = None,
    coordinates: CoordinatesArg = None,
    types: Annotated[
        list[FoodCategory] | None,
        Field(description="Tipos de estabelecimento (padrão: restaurant)"),
    ] = None,
    cuisine: Annotated[
        str | None,
        Field(description="Filtro de culinária do OSM, ex.: 'italian', 'pizza', 'japanese'"),
    ] = None,
    radius_km: RadiusArg = 5,
    limit: LimitArg = 10,
) -> PlaceSearchResult:
    """Busca restaurantes, cafés, bares e outras opções de alimentação próximas."""
    p = provider()
    center, resolved = await p.resolve_center(location, coordinates)
    places, total = await p.search_by_categories(
        center=center,
        categories=list(types or ["restaurant"]),
        radius_km=radius_km,
        limit=limit,
        cuisine=cuisine,
    )
    return PlaceSearchResult(
        center=center,
        resolved_location=resolved,
        radius_km=radius_km,
        places=places,
        total_found=total,
        notes=[] if places else ["Nenhum estabelecimento encontrado com esses filtros."],
    )


@mcp.tool(annotations=READ_ONLY)
@safe_tool
async def get_place_details(
    place_id: Annotated[str, Field(description="ID retornado pelas buscas, ex.: osm:node:123")],
) -> PlaceDetails:
    """Obtém detalhes de um lugar: horário bruto, site, telefone, acessibilidade e tags úteis."""
    return await provider().details(place_id)


def main() -> None:
    configure_logging()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
