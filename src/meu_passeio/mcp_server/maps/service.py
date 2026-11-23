"""Orquestra os providers de rotas: Google Routes (preferencial) e OSRM (alternativa).

O OSRM não considera trânsito nem pedágios e só aceita coordenadas; endereços são
geocodificados pelo Nominatim e IDs do Google não podem ser usados sem a chave.
"""

from __future__ import annotations

from datetime import datetime

from meu_passeio.mcp_server.common.google import get_google_client
from meu_passeio.mcp_server.common.http import ProviderError, build_client
from meu_passeio.mcp_server.maps import google as gmaps
from meu_passeio.mcp_server.maps.osrm import OsrmProvider
from meu_passeio.mcp_server.maps.schemas import (
    Leg,
    OptimizedStops,
    Route,
    RouteOptions,
    TollEstimate,
    TollInfo,
    TravelTimeMatrix,
)
from meu_passeio.mcp_server.places.service import osm
from meu_passeio.shared.schemas import Coordinates, TravelMode, Waypoint
from meu_passeio.texts import maps as T

_osrm: OsrmProvider | None = None


def osrm() -> OsrmProvider:
    global _osrm
    if _osrm is None:
        _osrm = OsrmProvider(build_client(timeout=20.0))
    return _osrm


def google_routes() -> gmaps.GoogleRoutesProvider | None:
    client = get_google_client()
    return gmaps.GoogleRoutesProvider(client) if client else None


async def to_coordinates(waypoint: Waypoint) -> Coordinates:
    if waypoint.coordinates is not None:
        return waypoint.coordinates
    if waypoint.address is not None:
        coords, _ = await osm().geocode(waypoint.address)
        return coords
    assert waypoint.place_id is not None
    if waypoint.place_id.startswith("osm:"):
        info = await osm().details(waypoint.place_id)
        if info.coordinates is not None:
            return info.coordinates
    raise ProviderError(T.Errors.GOOGLE_PLACE_ID_NEEDS_KEY)


def _fallback_note(exc: ProviderError | None) -> str:
    return T.Notes.GOOGLE_FAILED.format(error=exc) if exc else T.Notes.NO_GOOGLE_KEY


def _check_osrm_mode(mode: TravelMode) -> None:
    if mode == "transit":
        raise ProviderError(T.Errors.TRANSIT_NEEDS_GOOGLE)


async def route(
    origin: Waypoint,
    destination: Waypoint,
    *,
    mode: TravelMode,
    departure_time: datetime | None,
    alternatives: bool,
    avoid_tolls: bool,
    avoid_highways: bool,
    include_polyline: bool,
) -> RouteOptions:
    provider = google_routes()
    error: ProviderError | None = None
    if provider is not None:
        try:
            routes = await provider.compute_routes(
                origin,
                destination,
                mode=mode,
                departure_time=departure_time,
                alternatives=alternatives,
                avoid_tolls=avoid_tolls,
                avoid_highways=avoid_highways,
                include_polyline=include_polyline,
            )
            notes = [] if mode != "driving" else [T.Notes.TRAFFIC_AWARE]
            if departure_time is None and mode == "driving":
                notes.append(T.Notes.DEPARTURE_NOW)
            return RouteOptions(
                travel_mode=mode,
                departure_time=departure_time.isoformat() if departure_time else None,
                routes=[
                    Route(
                        **{k: v for k, v in r.items() if k not in ("optimized_order",)},
                        traffic_aware=mode == "driving",
                    )
                    for r in routes
                ],
                source=gmaps.SOURCE,
                notes=notes,
            )
        except ProviderError as exc:
            error = exc

    _check_osrm_mode(mode)
    a, b = await to_coordinates(origin), await to_coordinates(destination)
    data = await osrm().route(a, b, mode, include_polyline)
    return RouteOptions(
        travel_mode=mode,
        routes=[Route(**data, tolls=TollInfo())],
        source="osrm",
        notes=[_fallback_note(error), T.Notes.OSRM_LIMITS],
    )


async def tolls(
    origin: Waypoint,
    destination: Waypoint,
    *,
    round_trip: bool,
    departure_time: datetime | None,
) -> TollEstimate:
    provider = google_routes()
    if provider is None:
        raise ProviderError(T.Errors.TOLLS_NEED_GOOGLE)
    outbound_route = (
        await provider.compute_routes(origin, destination, departure_time=departure_time)
    )[0]
    outbound = TollInfo(**outbound_route["tolls"])
    inbound: TollInfo | None = None
    if round_trip:
        back = (await provider.compute_routes(destination, origin))[0]
        inbound = TollInfo(**back["tolls"])

    legs = [outbound] + ([inbound] if inbound else [])
    notes: list[str] = []
    if any(leg.has_tolls and leg.estimated_price is None for leg in legs):
        notes.append(T.Notes.TOLL_PRICE_UNKNOWN)
    known = [leg for leg in legs if leg.estimated_price is not None]
    currencies = {leg.currency for leg in known}
    total = (
        round(sum(leg.estimated_price or 0 for leg in known), 2)
        if known and len(currencies) == 1 and not notes
        else None
    )
    if not any(leg.has_tolls for leg in legs):
        total = 0.0
    notes.append(T.Notes.TOLL_ESTIMATE_DISCLAIMER)
    return TollEstimate(
        has_tolls=any(leg.has_tolls for leg in legs),
        outbound=outbound,
        inbound=inbound,
        total_estimated=total,
        currency=next(iter(currencies)) if len(currencies) == 1 else None,
        outbound_route=outbound_route.get("description"),
        source=gmaps.SOURCE,
        notes=notes,
    )


async def matrix(
    origins: list[Waypoint],
    destinations: list[Waypoint],
    *,
    mode: TravelMode,
    departure_time: datetime | None,
) -> TravelTimeMatrix:
    provider = google_routes()
    error: ProviderError | None = None
    if provider is not None:
        try:
            elements = await provider.matrix(
                origins, destinations, mode=mode, departure_time=departure_time
            )
            rows = len(origins)
            cols = len(destinations)
            durations: list[list[float | None]] = [[None] * cols for _ in range(rows)]
            static: list[list[float | None]] = [[None] * cols for _ in range(rows)]
            distances: list[list[float | None]] = [[None] * cols for _ in range(rows)]
            for el in elements:
                if el.get("condition") != "ROUTE_EXISTS":
                    continue
                i, j = el.get("originIndex", 0), el.get("destinationIndex", 0)
                durations[i][j] = gmaps.duration_seconds(el.get("duration"))
                static[i][j] = gmaps.duration_seconds(el.get("staticDuration"))
                distances[i][j] = el.get("distanceMeters")
            return TravelTimeMatrix(
                travel_mode=mode,
                durations_seconds=durations,
                static_durations_seconds=static,
                distances_meters=distances,
                traffic_aware=mode == "driving",
                source=gmaps.SOURCE,
            )
        except ProviderError as exc:
            error = exc

    _check_osrm_mode(mode)
    a = [await to_coordinates(w) for w in origins]
    b = [await to_coordinates(w) for w in destinations]
    data = await osrm().table(a, b, mode)
    return TravelTimeMatrix(
        travel_mode=mode,
        durations_seconds=data["durations"] or [],
        distances_meters=data["distances"],
        source="osrm",
        notes=[_fallback_note(error), T.Notes.OSRM_LIMITS],
    )


async def optimize(
    stops: list[Waypoint],
    *,
    mode: TravelMode,
    roundtrip: bool,
    departure_time: datetime | None,
) -> OptimizedStops:
    provider = google_routes()
    error: ProviderError | None = None
    if provider is not None:
        try:
            origin = stops[0]
            destination = stops[0] if roundtrip else stops[-1]
            middle = stops[1:] if roundtrip else stops[1:-1]
            result = (
                await provider.compute_routes(
                    origin,
                    destination,
                    mode=mode,
                    intermediates=middle,
                    optimize_order=bool(middle),
                    departure_time=departure_time,
                )
            )[0]
            optimized = result.get("optimized_order") or list(range(len(middle)))
            order = [0] + [i + 1 for i in optimized]
            if not roundtrip and len(stops) > 1:
                order.append(len(stops) - 1)
            return OptimizedStops(
                order=order,
                total_distance_meters=result["distance_meters"],
                total_duration_seconds=result["duration_seconds"],
                legs=[Leg(**leg) for leg in result["legs"]],
                roundtrip=roundtrip,
                travel_mode=mode,
                traffic_aware=mode == "driving",
                source=gmaps.SOURCE,
            )
        except ProviderError as exc:
            error = exc

    _check_osrm_mode(mode)
    coords = [await to_coordinates(w) for w in stops]
    data = await osrm().trip(coords, mode, roundtrip)
    return OptimizedStops(
        order=data["order"],
        total_distance_meters=data["distance_meters"],
        total_duration_seconds=data["duration_seconds"],
        roundtrip=roundtrip,
        travel_mode=mode,
        source="osrm",
        notes=[_fallback_note(error), T.Notes.OSRM_LIMITS],
    )
