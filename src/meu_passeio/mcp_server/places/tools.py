"""Tools de lugares — Google Places (preferencial) com OpenStreetMap como alternativa.

A escolha do provider e o fallback ficam em ``places/service.py``.
Textos (descrições, notas, erros): meu_passeio/texts/places.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.mcp_server.places import service
from meu_passeio.mcp_server.places.schemas import (
    FoodCategory,
    OpeningCheck,
    PlaceCategory,
    PlaceDetails,
    PlaceSearchResult,
    PriceLevel,
    RankBy,
)
from meu_passeio.shared.schemas import Coordinates, Waypoint
from meu_passeio.texts import places as T

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

LocationArg = Annotated[str | None, Field(description=T.Params.LOCATION)]
CoordinatesArg = Annotated[Coordinates | None, Field(description=T.Params.COORDINATES)]
RadiusArg = Annotated[float, Field(ge=0.5, le=50, description=T.Params.RADIUS_KM)]
LimitArg = Annotated[int, Field(ge=1, le=20, description=T.Params.LIMIT)]
MinRatingArg = Annotated[float | None, Field(ge=1, le=5, description=T.Params.MIN_RATING)]
MinReviewsArg = Annotated[int | None, Field(ge=0, description=T.Params.MIN_REVIEWS)]
OpenNowArg = Annotated[bool | None, Field(description=T.Params.OPEN_NOW)]
PriceLevelsArg = Annotated[list[PriceLevel] | None, Field(description=T.Params.PRICE_LEVELS)]
RankByArg = Annotated[RankBy, Field(description=T.Params.RANK_BY)]


@safe_tool
async def search_places(
    categories: Annotated[
        list[PlaceCategory] | None, Field(max_length=5, description=T.Params.CATEGORIES)
    ] = None,
    query: Annotated[str | None, Field(description=T.Params.QUERY)] = None,
    location: LocationArg = None,
    coordinates: CoordinatesArg = None,
    radius_km: RadiusArg = 10,
    min_rating: MinRatingArg = None,
    min_reviews: MinReviewsArg = None,
    open_now: OpenNowArg = None,
    price_levels: PriceLevelsArg = None,
    rank_by: RankByArg = "relevance",
    limit: LimitArg = 10,
) -> PlaceSearchResult:
    return await service.search(
        categories=list(categories) if categories else None,
        query=query,
        location=location,
        coordinates=coordinates,
        radius_km=radius_km,
        limit=limit,
        min_rating=min_rating,
        min_reviews=min_reviews,
        open_now=open_now,
        price_levels=list(price_levels) if price_levels else None,
        rank_by=rank_by,
    )


@safe_tool
async def search_restaurants(
    location: LocationArg = None,
    coordinates: CoordinatesArg = None,
    types: Annotated[
        list[FoodCategory] | None, Field(max_length=3, description=T.Params.FOOD_TYPES)
    ] = None,
    cuisine: Annotated[str | None, Field(description=T.Params.CUISINE)] = None,
    radius_km: RadiusArg = 5,
    min_rating: MinRatingArg = None,
    min_reviews: MinReviewsArg = None,
    open_now: OpenNowArg = None,
    price_levels: PriceLevelsArg = None,
    rank_by: RankByArg = "relevance",
    limit: LimitArg = 10,
) -> PlaceSearchResult:
    result = await service.search(
        categories=list(types or ["restaurant"]),
        query=None,
        location=location,
        coordinates=coordinates,
        radius_km=radius_km,
        limit=limit,
        min_rating=min_rating,
        min_reviews=min_reviews,
        open_now=open_now,
        price_levels=list(price_levels) if price_levels else None,
        rank_by=rank_by,
        cuisine=cuisine,
    )
    if not result.places:
        result.notes = [n for n in result.notes if n != T.Notes.NO_PLACES] + [
            T.Notes.NO_RESTAURANTS
        ]
    return result


@safe_tool
async def get_place_details(
    place_id: Annotated[str, Field(description=T.Params.PLACE_ID)],
) -> PlaceDetails:
    return await service.details(place_id)


@safe_tool
async def check_opening_hours(
    place_id: Annotated[str, Field(description=T.Params.PLACE_ID)],
    datetime_local: Annotated[datetime, Field(description=T.Params.DATETIME_LOCAL)],
) -> OpeningCheck:
    return await service.check_opening(place_id, datetime_local.replace(tzinfo=None))


@safe_tool
async def find_nearby(
    categories: Annotated[
        list[PlaceCategory | FoodCategory],
        Field(min_length=1, max_length=5, description=T.Params.NEARBY_CATEGORIES),
    ],
    place_id: Annotated[str | None, Field(description=T.Params.NEARBY_PLACE_ID)] = None,
    coordinates: Annotated[
        Coordinates | None, Field(description=T.Params.NEARBY_COORDINATES)
    ] = None,
    radius_m: Annotated[float, Field(ge=100, le=50_000, description=T.Params.RADIUS_M)] = 1000,
    min_rating: MinRatingArg = None,
    min_reviews: MinReviewsArg = None,
    rank_by: RankByArg = "relevance",
    limit: LimitArg = 10,
) -> PlaceSearchResult:
    return await service.nearby(
        place_id=place_id,
        coordinates=coordinates,
        categories=list(categories),
        radius_m=radius_m,
        limit=limit,
        rank_by=rank_by,
        min_rating=min_rating,
        min_reviews=min_reviews,
    )


@safe_tool
async def search_along_route(
    origin: Waypoint,
    destination: Waypoint,
    query: Annotated[str, Field(min_length=2, description=T.Params.ALONG_ROUTE_QUERY)],
    min_rating: MinRatingArg = None,
    open_now: OpenNowArg = None,
    limit: LimitArg = 10,
) -> PlaceSearchResult:
    return await service.along_route(
        origin=origin,
        destination=destination,
        query=query,
        limit=limit,
        min_rating=min_rating,
        open_now=open_now,
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(search_places, description=T.Tools.SEARCH_PLACES, annotations=READ_ONLY)
    mcp.add_tool(search_restaurants, description=T.Tools.SEARCH_RESTAURANTS, annotations=READ_ONLY)
    mcp.add_tool(get_place_details, description=T.Tools.GET_PLACE_DETAILS, annotations=READ_ONLY)
    mcp.add_tool(
        check_opening_hours, description=T.Tools.CHECK_OPENING_HOURS, annotations=READ_ONLY
    )
    mcp.add_tool(find_nearby, description=T.Tools.FIND_NEARBY, annotations=READ_ONLY)
    mcp.add_tool(search_along_route, description=T.Tools.SEARCH_ALONG_ROUTE, annotations=READ_ONLY)
