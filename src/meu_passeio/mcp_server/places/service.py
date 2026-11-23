"""Orquestra os providers de lugares: Google Places (preferencial) e OpenStreetMap (alternativa).

- Com GOOGLE_MAPS_API_KEY configurada, as buscas usam o Google; se o Google falhar, a busca
  cai para o OSM e o resultado informa isso em ``notes``.
- Sem chave, tudo usa o OSM (sem avaliações, preços ou horários estruturados).
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta

from meu_passeio.mcp_server.common.google import get_google_client
from meu_passeio.mcp_server.common.http import ProviderError, build_client
from meu_passeio.mcp_server.maps.google import GoogleRoutesProvider
from meu_passeio.mcp_server.places.google import CATEGORY_TO_GOOGLE, GooglePlacesProvider
from meu_passeio.mcp_server.places.opening_hours import opening_status
from meu_passeio.mcp_server.places.osm import OsmPlacesProvider
from meu_passeio.mcp_server.places.schemas import (
    OpeningCheck,
    Place,
    PlaceDetails,
    PlaceSearchResult,
)
from meu_passeio.shared.schemas import Coordinates, Waypoint
from meu_passeio.texts import places as T

# Prior bayesiano para ordenar por qualidade: evita que 5,0 com 3 avaliações vença 4,7 com 3 mil.
PRIOR_RATING = 4.0
PRIOR_WEIGHT = 50

_osm: OsmPlacesProvider | None = None


def osm() -> OsmPlacesProvider:
    global _osm
    if _osm is None:
        _osm = OsmPlacesProvider(build_client(timeout=30.0))
    return _osm


def google() -> GooglePlacesProvider | None:
    client = get_google_client()
    return GooglePlacesProvider(client) if client else None


def quality_score(place: Place) -> float:
    if place.rating is None:
        return 0.0
    count = place.user_rating_count or 0
    bayes = (count * place.rating + PRIOR_WEIGHT * PRIOR_RATING) / (count + PRIOR_WEIGHT)
    return bayes + math.log10(count + 1) * 0.01


def rank(places: list[Place], rank_by: str) -> list[Place]:
    if rank_by == "distance":
        return sorted(places, key=lambda p: p.distance_km if p.distance_km is not None else 1e9)
    if rank_by == "popularity":
        return sorted(places, key=lambda p: p.user_rating_count or 0, reverse=True)
    return sorted(places, key=quality_score, reverse=True)


def _merge(groups: list[list[Place]]) -> list[Place]:
    seen: dict[str, Place] = {}
    for group in groups:
        for place in group:
            seen.setdefault(place.id, place)
    return list(seen.values())


def _query(*parts: str | None) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


async def resolve_center(
    location: str | None, coordinates: Coordinates | None
) -> tuple[Coordinates | None, str | None]:
    """Geocodifica pelo Nominatim (gratuito). Falha não é fatal quando há Google."""
    if coordinates is not None:
        return coordinates, None
    if not location:
        raise ProviderError(T.Errors.MISSING_LOCATION)
    try:
        return await osm().geocode(location)
    except ProviderError:
        if google() is None:
            raise
        return None, None


async def _osm_search(
    *,
    categories: list[str] | None,
    query: str | None,
    center: Coordinates,
    radius_km: float,
    limit: int,
    cuisine: str | None = None,
) -> tuple[list[Place], int]:
    if categories:
        return await osm().search_by_categories(
            center=center,
            categories=categories,
            radius_km=radius_km,
            limit=limit,
            name_contains=query,
            cuisine=cuisine,
        )
    if query:
        return await osm().search_by_text(
            query=query, center=center, radius_km=radius_km, limit=limit
        )
    raise ProviderError(T.Errors.MISSING_SEARCH)


async def search(
    *,
    categories: list[str] | None,
    query: str | None,
    location: str | None,
    coordinates: Coordinates | None,
    radius_km: float,
    limit: int,
    min_rating: float | None = None,
    min_reviews: int | None = None,
    open_now: bool | None = None,
    price_levels: list[str] | None = None,
    rank_by: str = "relevance",
    cuisine: str | None = None,
) -> PlaceSearchResult:
    if not categories and not query:
        raise ProviderError(T.Errors.MISSING_SEARCH)
    center, resolved = await resolve_center(location, coordinates)
    notes: list[str] = []
    provider = google()

    if provider is not None:
        try:
            jobs = []
            for category in categories or [None]:
                included_type, term = (
                    CATEGORY_TO_GOOGLE.get(category, (None, None)) if category else (None, None)
                )
                text = _query(cuisine, term, query, f"{T.NEAR} {location}" if location else None)
                jobs.append(
                    provider.text_search(
                        text_query=text,
                        center=center,
                        radius_km=radius_km,
                        limit=limit,
                        included_type=included_type,
                        min_rating=min_rating,
                        min_reviews=min_reviews,
                        open_now=open_now,
                        price_levels=price_levels,
                        rank_by_distance=rank_by == "distance",
                    )
                )
            results = await asyncio.gather(*jobs)
            places = rank(_merge([r[0] for r in results]), rank_by)
            if not places:
                notes.append(T.Notes.NO_PLACES)
            return PlaceSearchResult(
                center=center,
                resolved_location=resolved,
                radius_km=radius_km,
                places=places[:limit],
                total_found=len(places),
                source=T.Sources.GOOGLE,
                attribution=T.ATTRIBUTION,
                notes=notes,
            )
        except ProviderError as exc:
            notes.append(T.Notes.GOOGLE_FAILED.format(error=exc))
    else:
        notes.append(T.Notes.NO_GOOGLE_KEY)

    if center is None:
        raise ProviderError(T.Errors.MISSING_LOCATION)
    places, total = await _osm_search(
        categories=categories,
        query=query,
        center=center,
        radius_km=radius_km,
        limit=limit,
        cuisine=cuisine,
    )
    if not places:
        notes.append(T.Notes.NO_PLACES)
    return PlaceSearchResult(
        center=center,
        resolved_location=resolved,
        radius_km=radius_km,
        places=places,
        total_found=total,
        source=T.Sources.OSM,
        notes=notes,
    )


async def details(place_id: str) -> PlaceDetails:
    if place_id.startswith("osm:"):
        return await osm().details(place_id)
    provider = google()
    if provider is None:
        raise ProviderError(T.Errors.GOOGLE_REQUIRED)
    return await provider.details(place_id)


async def check_opening(place_id: str, at: datetime) -> OpeningCheck:
    if place_id.startswith("osm:"):
        info = await osm().details(place_id)
        return OpeningCheck(
            place_id=place_id,
            name=info.name,
            datetime_local=at.isoformat(timespec="minutes"),
            is_open=None,
            opening_hours_weekdays=[info.opening_hours] if info.opening_hours else [],
            source=T.Sources.OSM,
            notes=[T.Notes.OSM_HOURS_UNPARSED],
        )
    provider = google()
    if provider is None:
        raise ProviderError(T.Errors.GOOGLE_REQUIRED)
    raw = await provider.opening_hours(place_id)
    regular = raw.get("regularOpeningHours") or {}
    current = raw.get("currentOpeningHours") or {}
    notes: list[str] = []
    # currentOpeningHours cobre os próximos 7 dias e inclui feriados/horários especiais.
    use_current = bool(current.get("periods")) and at.date() < datetime.now().date() + timedelta(
        days=7
    )
    periods = current.get("periods") if use_current else regular.get("periods")
    if not use_current:
        notes.append(T.Notes.REGULAR_HOURS_ONLY)
    status = opening_status(periods, at)
    if status.is_open is None:
        notes.append(T.Notes.NO_HOURS)
    return OpeningCheck(
        place_id=place_id,
        name=(raw.get("displayName") or {}).get("text"),
        datetime_local=at.isoformat(timespec="minutes"),
        is_open=status.is_open,
        opens_at=status.opens_at,
        closes_at=status.closes_at,
        opening_hours_weekdays=regular.get("weekdayDescriptions", []),
        business_status=raw.get("businessStatus"),
        source=T.Sources.GOOGLE,
        notes=notes,
    )


async def _place_center(place_id: str) -> Coordinates:
    info = await details(place_id)
    if info.coordinates is None:
        raise ProviderError(T.Errors.PLACE_WITHOUT_LOCATION.format(place_id=place_id))
    return info.coordinates


async def nearby(
    *,
    place_id: str | None,
    coordinates: Coordinates | None,
    categories: list[str],
    radius_m: float,
    limit: int,
    rank_by: str,
    min_rating: float | None,
    min_reviews: int | None,
) -> PlaceSearchResult:
    if (place_id is None) == (coordinates is None):
        raise ProviderError(T.Errors.NEARBY_ONE_ORIGIN)
    center = coordinates or await _place_center(place_id)  # type: ignore[arg-type]
    notes: list[str] = []
    provider = google()
    if provider is not None:
        try:
            typed = [CATEGORY_TO_GOOGLE[c][0] for c in categories if CATEGORY_TO_GOOGLE[c][0]]
            untyped = [CATEGORY_TO_GOOGLE[c][1] for c in categories if not CATEGORY_TO_GOOGLE[c][0]]
            jobs = []
            if typed:
                jobs.append(
                    provider.nearby_search(
                        center=center,
                        radius_m=radius_m,
                        included_types=typed,
                        limit=limit,
                        rank_by_distance=rank_by == "distance",
                        min_rating=min_rating,
                        min_reviews=min_reviews,
                    )
                )
            for term in untyped:
                jobs.append(
                    provider.text_search(
                        text_query=term,
                        center=center,
                        radius_km=radius_m / 1000,
                        limit=limit,
                        min_rating=min_rating,
                        min_reviews=min_reviews,
                        rank_by_distance=True,
                    )
                )
            results = await asyncio.gather(*jobs)
            places = rank(_merge([r[0] for r in results]), rank_by)
            return PlaceSearchResult(
                center=center,
                radius_km=radius_m / 1000,
                places=places[:limit],
                total_found=len(places),
                source=T.Sources.GOOGLE,
                attribution=T.ATTRIBUTION,
                notes=[] if places else [T.Notes.NO_PLACES],
            )
        except ProviderError as exc:
            notes.append(T.Notes.GOOGLE_FAILED.format(error=exc))
    else:
        notes.append(T.Notes.NO_GOOGLE_KEY)
    places, total = await osm().search_by_categories(
        center=center, categories=categories, radius_km=radius_m / 1000, limit=limit
    )
    return PlaceSearchResult(
        center=center,
        radius_km=radius_m / 1000,
        places=places,
        total_found=total,
        source=T.Sources.OSM,
        notes=notes + ([] if places else [T.Notes.NO_PLACES]),
    )


async def along_route(
    *,
    origin: Waypoint,
    destination: Waypoint,
    query: str,
    limit: int,
    min_rating: float | None,
    open_now: bool | None,
) -> PlaceSearchResult:
    client = get_google_client()
    if client is None:
        raise ProviderError(T.Errors.GOOGLE_REQUIRED)
    route = (
        await GoogleRoutesProvider(client).compute_routes(
            origin, destination, include_polyline=True
        )
    )[0]
    if not route.get("polyline"):
        raise ProviderError(T.Errors.ROUTE_WITHOUT_POLYLINE)
    places, total = await GooglePlacesProvider(client).text_search(
        text_query=query,
        center=None,
        radius_km=None,
        limit=limit,
        min_rating=min_rating,
        open_now=open_now,
        route_polyline=route["polyline"],
    )
    return PlaceSearchResult(
        places=places,
        total_found=total,
        source=T.Sources.GOOGLE,
        attribution=T.ATTRIBUTION,
        notes=[
            T.Notes.ALONG_ROUTE_SUMMARY.format(
                km=round(route["distance_meters"] / 1000, 1),
                minutes=round(route["duration_seconds"] / 60),
            )
        ]
        + ([] if places else [T.Notes.NO_PLACES]),
    )
