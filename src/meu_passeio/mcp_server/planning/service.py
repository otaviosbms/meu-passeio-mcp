"""Planejamento: sugestão de bate-voltas e montagem da agenda de um dia.

- ``suggest_day_trips``: procura atrações bem avaliadas num raio compatível com o tempo
  máximo de carro, agrupa por município e confirma o tempo real de viagem (com trânsito)
  pela matriz de rotas do Google.
- ``plan_day``: ordena as paradas (otimização do Google ou OSRM), calcula horários de
  chegada/saída e confere o horário de funcionamento de cada lugar na chegada.
"""

from __future__ import annotations

import asyncio
import math
from datetime import date, datetime, timedelta
from typing import Any

from meu_passeio.mcp_server.common.google import get_google_client
from meu_passeio.mcp_server.common.http import ProviderError
from meu_passeio.mcp_server.maps import service as maps
from meu_passeio.mcp_server.maps.google import GoogleRoutesProvider, duration_seconds
from meu_passeio.mcp_server.places import service as places
from meu_passeio.mcp_server.places.google import CATEGORY_TO_GOOGLE, GooglePlacesProvider
from meu_passeio.mcp_server.places.opening_hours import opening_status
from meu_passeio.mcp_server.places.schemas import Place
from meu_passeio.mcp_server.planning.schemas import (
    Attraction,
    DayItinerary,
    DayStop,
    DayTripDestination,
    DayTripSuggestions,
    ScheduledStop,
)
from meu_passeio.shared.schemas import Coordinates, TravelMode, Waypoint
from meu_passeio.texts import planning as T
from meu_passeio.texts.places import ATTRIBUTION

AVERAGE_ROAD_SPEED_KMH = 80  # raio de busca = horas × velocidade média (depois confirmado)
MAX_SEARCH_RADIUS_KM = 300
MAX_MATRIX_DESTINATIONS = 25
TOP_ATTRACTIONS_PER_TOWN = 5
MAX_WAIT_MINUTES = 180
DEFAULT_INTERESTS = ["tourist_attraction", "waterfall", "viewpoint", "park"]


# ------------------------------------------------------------------------- bate-volta


def _rectangle(center: Coordinates, radius_km: float) -> tuple[Coordinates, Coordinates]:
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(math.cos(math.radians(center.latitude)), 0.1))
    return (
        Coordinates(
            latitude=max(center.latitude - dlat, -90), longitude=max(center.longitude - dlon, -180)
        ),
        Coordinates(
            latitude=min(center.latitude + dlat, 90), longitude=min(center.longitude + dlon, 180)
        ),
    )


def _attraction(place: Place) -> Attraction:
    return Attraction(
        id=place.id,
        name=place.name,
        category_label=place.category_label,
        rating=place.rating,
        user_rating_count=place.user_rating_count,
        coordinates=place.coordinates,
        google_maps_uri=place.google_maps_uri,
    )


async def suggest_day_trips(
    *,
    origin: str | None,
    origin_coordinates: Coordinates | None,
    max_drive_hours: float,
    interests: list[str] | None,
    min_rating: float,
    min_reviews: int,
    min_distance_km: float,
    departure_time: datetime | None,
    limit: int,
) -> DayTripSuggestions:
    client = get_google_client()
    if client is None:
        raise ProviderError(T.Errors.GOOGLE_REQUIRED)
    center, label = await places.resolve_center(origin, origin_coordinates)
    if center is None:
        raise ProviderError(T.Errors.ORIGIN_NOT_FOUND)

    radius_km = min(max_drive_hours * AVERAGE_ROAD_SPEED_KMH, MAX_SEARCH_RADIUS_KM)
    rectangle = _rectangle(center, radius_km)
    provider = GooglePlacesProvider(client)
    jobs = []
    for interest in interests or DEFAULT_INTERESTS:
        included_type, term = CATEGORY_TO_GOOGLE[interest]
        jobs.append(
            provider.text_search(
                text_query=term,
                center=center,
                radius_km=None,
                limit=20,
                included_type=included_type,
                min_rating=min_rating,
                min_reviews=min_reviews,
                rectangle=rectangle,
                with_address_components=True,
            )
        )
    results = await asyncio.gather(*jobs)
    candidates = places._merge([r[0] for r in results])

    by_town: dict[tuple[str, str | None], list[Place]] = {}
    for place in candidates:
        if not place.town or place.coordinates is None or place.distance_km is None:
            continue
        if not (min_distance_km <= place.distance_km <= radius_km):
            continue
        by_town.setdefault((place.town, place.state_code), []).append(place)

    ranked_towns = []
    for key, items in by_town.items():
        items = places.rank(items, "relevance")
        score = sum(places.quality_score(p) for p in items[:3])
        ranked_towns.append((score, key, items))
    ranked_towns.sort(key=lambda t: t[0], reverse=True)
    shortlist = ranked_towns[:MAX_MATRIX_DESTINATIONS]

    notes = [T.Notes.DAY_TRIP_METHOD]
    destinations: list[DayTripDestination] = []
    if shortlist:
        routes = GoogleRoutesProvider(client)
        elements = await routes.matrix(
            [Waypoint(coordinates=center)],
            [Waypoint(coordinates=items[0].coordinates) for _, _, items in shortlist],
            departure_time=departure_time,
        )
        drive: dict[int, dict[str, Any]] = {
            el.get("destinationIndex", 0): el
            for el in elements
            if el.get("condition") == "ROUTE_EXISTS"
        }
        for index, (score, (town, state), items) in enumerate(shortlist):
            element = drive.get(index)
            if element is None:
                continue
            seconds = duration_seconds(element.get("duration")) or 0
            if seconds > max_drive_hours * 3600:
                continue
            static = duration_seconds(element.get("staticDuration"))
            destinations.append(
                DayTripDestination(
                    town=town,
                    state_code=state,
                    drive_minutes=round(seconds / 60),
                    drive_minutes_no_traffic=round(static / 60) if static else None,
                    distance_km=round((element.get("distanceMeters") or 0) / 1000, 1),
                    score=round(score, 2),
                    attraction_count=len(items),
                    top_attractions=[_attraction(p) for p in items[:TOP_ATTRACTIONS_PER_TOWN]],
                )
            )
    destinations = destinations[:limit]
    if not destinations:
        notes.append(T.Notes.NO_DAY_TRIPS)
    return DayTripSuggestions(
        origin=center,
        origin_label=label,
        max_drive_hours=max_drive_hours,
        destinations=destinations,
        candidates_considered=len(candidates),
        attribution=ATTRIBUTION,
        notes=notes,
    )


# ----------------------------------------------------------------------- agenda do dia


def _clock(value: datetime) -> str:
    return value.strftime("%H:%M")


def _label(stop: DayStop, index: int) -> str:
    if stop.name:
        return stop.name
    if stop.place.address:
        return stop.place.address
    return T.UNNAMED_STOP.format(n=index + 1)


async def _legs_google(
    provider: GoogleRoutesProvider,
    start: Waypoint,
    end: Waypoint,
    stops: list[DayStop],
    *,
    mode: TravelMode,
    optimize: bool,
    departure: datetime | None,
) -> tuple[list[int], list[dict[str, int]]]:
    route = (
        await provider.compute_routes(
            start,
            end,
            mode=mode,
            intermediates=[s.place for s in stops],
            optimize_order=optimize,
            departure_time=departure,
        )
    )[0]
    order = route.get("optimized_order") or list(range(len(stops)))
    return order, route["legs"]


async def _legs_osrm(
    start: Waypoint, end: Waypoint, stops: list[DayStop], *, mode: TravelMode, optimize: bool
) -> tuple[list[int], list[dict[str, int]]]:
    coords = [await maps.to_coordinates(w) for w in [start, *(s.place for s in stops), end]]
    order = list(range(len(stops)))
    if optimize and len(stops) > 1:
        # Ida e volta deixa o OSRM livre para ordenar todas as paradas; giramos para o início.
        sequence_ids = (await maps.osrm().trip(coords[:-1], mode, roundtrip=True))["order"]
        k = sequence_ids.index(0)
        order = [i - 1 for i in sequence_ids[k + 1 :] + sequence_ids[:k]]
    sequence = [coords[0], *(coords[i + 1] for i in order), coords[-1]]
    legs = []
    for a, b in zip(sequence, sequence[1:], strict=False):
        data = await maps.osrm().route(a, b, mode, False)
        legs.append(
            {
                "distance_meters": data["distance_meters"],
                "duration_seconds": data["duration_seconds"],
            }
        )
    return order, legs


async def _hours(stops: list[DayStop], day: date) -> dict[int, list[dict[str, Any]] | None]:
    """Busca os períodos de funcionamento das paradas com place_id do Google."""
    provider = places.google()
    if provider is None:
        return {}
    use_current = day < date.today() + timedelta(days=7)
    indexed = [
        (i, s.place.place_id)
        for i, s in enumerate(stops)
        if s.place.place_id and not s.place.place_id.startswith("osm:")
    ]
    results = await asyncio.gather(
        *(provider.opening_hours(pid) for _, pid in indexed), return_exceptions=True
    )
    hours: dict[int, list[dict[str, Any]] | None] = {}
    for (i, _), raw in zip(indexed, results, strict=True):
        if isinstance(raw, BaseException):
            hours[i] = None
            continue
        current = (raw.get("currentOpeningHours") or {}).get("periods")
        regular = (raw.get("regularOpeningHours") or {}).get("periods")
        hours[i] = current if (use_current and current) else regular
        if not stops[i].name:
            stops[i].name = (raw.get("displayName") or {}).get("text")
    return hours


async def plan_day(
    *,
    start: Waypoint,
    stops: list[DayStop],
    day: date,
    start_time: str,
    end: Waypoint | None,
    mode: TravelMode,
    keep_order: bool,
) -> DayItinerary:
    try:
        hour, minute = (int(x) for x in start_time.split(":"))
        clock = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)
    except ValueError as exc:
        raise ProviderError(T.Errors.INVALID_START_TIME) from exc
    end = end or start
    optimize = not keep_order and len(stops) > 1
    notes: list[str] = []

    routes = maps.google_routes()
    source, traffic_aware = "osrm", False
    legs: list[dict[str, int]] = []
    order: list[int] = []
    if routes is not None:
        try:
            departure = clock if clock > datetime.now() + timedelta(minutes=1) else None
            order, legs = await _legs_google(
                routes, start, end, stops, mode=mode, optimize=optimize, departure=departure
            )
            source, traffic_aware = "google_maps", mode == "driving" and departure is not None
            if traffic_aware:
                notes.append(T.Notes.TRAFFIC_AT_START)
        except ProviderError as exc:
            notes.append(T.Notes.GOOGLE_FAILED.format(error=exc))
    else:
        notes.append(T.Notes.NO_GOOGLE_KEY)
    if not legs:
        if mode == "transit":
            raise ProviderError(T.Errors.TRANSIT_NEEDS_GOOGLE)
        order, legs = await _legs_osrm(start, end, stops, mode=mode, optimize=optimize)

    hours = await _hours(stops, day)
    if not hours:
        notes.append(T.Notes.NO_HOURS_CHECK)

    scheduled: list[ScheduledStop] = []
    warnings: list[str] = []
    for position, index in enumerate(order):
        stop, leg = stops[index], legs[position]
        name = _label(stop, index)
        clock += timedelta(seconds=leg["duration_seconds"])
        arrival = clock
        stop_warnings: list[str] = []
        wait = 0
        is_open: bool | None = None
        closes_at: str | None = None
        periods = hours.get(index)
        if periods:
            status = opening_status(periods, arrival)
            is_open = status.is_open
            if status.is_open is False and status.next_open is not None:
                gap = (status.next_open - arrival).total_seconds() / 60
                if status.next_open.date() == arrival.date() and gap <= MAX_WAIT_MINUTES:
                    wait = round(gap)
                    clock = status.next_open
                    stop_warnings.append(T.Warnings.WAIT.format(minutes=wait, opens=_clock(clock)))
                    status = opening_status(periods, clock)
                else:
                    stop_warnings.append(T.Warnings.CLOSED.format(opens=status.opens_at))
            if status.open_until is not None:
                closes_at = _clock(status.open_until)
                if clock + timedelta(minutes=stop.visit_minutes) > status.open_until:
                    stop_warnings.append(T.Warnings.CLOSES_DURING_VISIT.format(closes=closes_at))
        visit_start = clock
        clock += timedelta(minutes=stop.visit_minutes)
        if clock.date() != day:
            stop_warnings.append(T.Warnings.PAST_MIDNIGHT)
        warnings.extend(f"{name}: {w}" for w in stop_warnings)
        scheduled.append(
            ScheduledStop(
                order=position + 1,
                input_index=index,
                name=name,
                place_id=stop.place.place_id,
                arrival=_clock(arrival),
                visit_start=_clock(visit_start),
                departure=_clock(clock),
                travel_minutes_from_previous=round(leg["duration_seconds"] / 60),
                distance_km_from_previous=round(leg["distance_meters"] / 1000, 1),
                wait_minutes=wait,
                is_open_on_arrival=is_open,
                closes_at=closes_at,
                warnings=stop_warnings,
            )
        )
    final_leg = (
        legs[len(order)]
        if len(legs) > len(order)
        else {"duration_seconds": 0, "distance_meters": 0}
    )
    clock += timedelta(seconds=final_leg["duration_seconds"])
    return DayItinerary(
        date=day.isoformat(),
        start_time=start_time,
        end_arrival=_clock(clock),
        stops=scheduled,
        total_travel_minutes=round(sum(leg["duration_seconds"] for leg in legs) / 60),
        total_distance_km=round(sum(leg["distance_meters"] for leg in legs) / 1000, 1),
        total_visit_minutes=sum(s.visit_minutes for s in stops),
        order_optimized=optimize,
        traffic_aware=traffic_aware,
        source=source,
        notes=notes,
        warnings=warnings,
    )
