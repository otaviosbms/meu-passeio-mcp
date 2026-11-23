"""Places MCP Server — descoberta e detalhes de locais (OpenStreetMap).

Execução (stdio):  python -m meu_passeio.mcp_servers.places
Textos (descrições, notas, erros): meu_passeio/texts/places.py
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
from meu_passeio.texts import places as T

mcp = MCPServer(name="meu-passeio-places", instructions=T.INSTRUCTIONS)

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
_provider: OsmPlacesProvider | None = None


def provider() -> OsmPlacesProvider:
    global _provider
    if _provider is None:
        _provider = OsmPlacesProvider(build_client(timeout=30.0))
    return _provider


LocationArg = Annotated[str | None, Field(description=T.Params.LOCATION)]
CoordinatesArg = Annotated[Coordinates | None, Field(description=T.Params.COORDINATES)]
RadiusArg = Annotated[float, Field(ge=0.5, le=100, description=T.Params.RADIUS_KM)]
LimitArg = Annotated[int, Field(ge=1, le=30, description=T.Params.LIMIT)]


@mcp.tool(description=T.Tools.SEARCH_PLACES, annotations=READ_ONLY)
@safe_tool
async def search_places(
    categories: Annotated[
        list[PlaceCategory] | None, Field(description=T.Params.CATEGORIES)
    ] = None,
    query: Annotated[str | None, Field(description=T.Params.QUERY)] = None,
    location: LocationArg = None,
    coordinates: CoordinatesArg = None,
    radius_km: RadiusArg = 10,
    limit: LimitArg = 10,
) -> PlaceSearchResult:
    p = provider()
    center, resolved = await p.resolve_center(location, coordinates)
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
        raise ValueError(T.Errors.MISSING_SEARCH)
    return PlaceSearchResult(
        center=center,
        resolved_location=resolved,
        radius_km=radius_km,
        places=places,
        total_found=total,
        notes=[] if places else [T.Notes.NO_PLACES],
    )


@mcp.tool(description=T.Tools.SEARCH_RESTAURANTS, annotations=READ_ONLY)
@safe_tool
async def search_restaurants(
    location: LocationArg = None,
    coordinates: CoordinatesArg = None,
    types: Annotated[list[FoodCategory] | None, Field(description=T.Params.FOOD_TYPES)] = None,
    cuisine: Annotated[str | None, Field(description=T.Params.CUISINE)] = None,
    radius_km: RadiusArg = 5,
    limit: LimitArg = 10,
) -> PlaceSearchResult:
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
        notes=[] if places else [T.Notes.NO_RESTAURANTS],
    )


@mcp.tool(description=T.Tools.GET_PLACE_DETAILS, annotations=READ_ONLY)
@safe_tool
async def get_place_details(
    place_id: Annotated[str, Field(description=T.Params.PLACE_ID)],
) -> PlaceDetails:
    return await provider().details(place_id)


def main() -> None:
    configure_logging()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
