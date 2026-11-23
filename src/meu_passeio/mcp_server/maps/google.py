"""Provider de rotas baseado na Google Routes API.

Docs: https://developers.google.com/maps/documentation/routes
- Durações de carro consideram o trânsito (``TRAFFIC_AWARE``) para o horário de saída.
- Pedágios: ``extraComputations: TOLLS`` devolve o custo estimado em moeda local quando o
  Google conhece as tarifas; quando só sabe que há pedágio, ``estimated_price`` fica vazio.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from meu_passeio.mcp_server.common.google import (
    GoogleMapsClient,
    duration_seconds,
    money_to_float,
)
from meu_passeio.mcp_server.common.http import ProviderError
from meu_passeio.shared.schemas import TravelMode, Waypoint
from meu_passeio.texts import maps as T

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
SOURCE = "google_maps"
BRASILIA = timezone(timedelta(hours=-3))

MODES: dict[str, str] = {
    "driving": "DRIVE",
    "walking": "WALK",
    "cycling": "BICYCLE",
    "transit": "TRANSIT",
}

ROUTE_FIELDS = [
    "routes.distanceMeters",
    "routes.duration",
    "routes.staticDuration",
    "routes.description",
    "routes.warnings",
    "routes.travelAdvisory.tollInfo",
    "routes.optimizedIntermediateWaypointIndex",
    "routes.legs.distanceMeters",
    "routes.legs.duration",
]
MATRIX_FIELDS = (
    "originIndex,destinationIndex,status,condition,distanceMeters,duration,staticDuration"
)


def waypoint_body(waypoint: Waypoint) -> dict[str, Any]:
    if waypoint.coordinates is not None:
        return {
            "location": {
                "latLng": {
                    "latitude": waypoint.coordinates.latitude,
                    "longitude": waypoint.coordinates.longitude,
                }
            }
        }
    if waypoint.place_id is not None:
        if waypoint.place_id.startswith("osm:"):
            raise ProviderError(T.Errors.OSM_ID_IN_GOOGLE_ROUTE)
        return {"placeId": waypoint.place_id}
    return {"address": waypoint.address}


def _rfc3339(value: datetime) -> str:
    """Horário sem fuso é tratado como horário de Brasília (UTC-3, sem horário de verão)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=BRASILIA)
    if value < datetime.now(UTC):
        raise ProviderError(T.Errors.DEPARTURE_IN_PAST)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_tolls(route: dict[str, Any]) -> dict[str, Any]:
    """Interpreta ``travelAdvisory.tollInfo``: ausente = sem pedágio conhecido."""
    advisory = route.get("travelAdvisory") or {}
    if "tollInfo" not in advisory:
        return {"has_tolls": False, "estimated_price": None, "currency": None}
    prices = (advisory.get("tollInfo") or {}).get("estimatedPrice") or []
    if not prices:
        return {"has_tolls": True, "estimated_price": None, "currency": None}
    # Normalmente há uma única moeda; somamos por segurança se vierem várias da mesma moeda.
    currency = prices[0].get("currencyCode")
    total = sum(money_to_float(p) or 0 for p in prices if p.get("currencyCode") == currency)
    return {"has_tolls": True, "estimated_price": round(total, 2), "currency": currency}


def parse_route(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "distance_meters": route.get("distanceMeters") or 0,
        "duration_seconds": duration_seconds(route.get("duration")) or 0,
        "static_duration_seconds": duration_seconds(route.get("staticDuration")),
        "description": route.get("description"),
        "warnings": route.get("warnings") or [],
        "tolls": parse_tolls(route),
        "polyline": (route.get("polyline") or {}).get("encodedPolyline"),
        "optimized_order": route.get("optimizedIntermediateWaypointIndex"),
        "legs": [
            {
                "distance_meters": leg.get("distanceMeters") or 0,
                "duration_seconds": duration_seconds(leg.get("duration")) or 0,
            }
            for leg in route.get("legs") or []
        ],
    }


class GoogleRoutesProvider:
    def __init__(self, client: GoogleMapsClient) -> None:
        self._client = client

    def _base_body(self, mode: TravelMode, departure_time: datetime | None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "travelMode": MODES[mode],
            "languageCode": self._client.language,
            "regionCode": self._client.region.lower(),
            "units": "METRIC",
        }
        if mode == "driving":
            body["routingPreference"] = "TRAFFIC_AWARE"
        if departure_time is not None:
            body["departureTime"] = _rfc3339(departure_time)
        return body

    async def compute_routes(
        self,
        origin: Waypoint,
        destination: Waypoint,
        *,
        mode: TravelMode = "driving",
        intermediates: list[Waypoint] | None = None,
        departure_time: datetime | None = None,
        alternatives: bool = False,
        avoid_tolls: bool = False,
        avoid_highways: bool = False,
        optimize_order: bool = False,
        include_polyline: bool = False,
    ) -> list[dict[str, Any]]:
        body = self._base_body(mode, departure_time)
        body["origin"] = waypoint_body(origin)
        body["destination"] = waypoint_body(destination)
        if intermediates:
            body["intermediates"] = [waypoint_body(w) for w in intermediates]
            if optimize_order:
                body["optimizeWaypointOrder"] = True
        if alternatives and not intermediates:
            body["computeAlternativeRoutes"] = True
        if mode == "driving":
            body["extraComputations"] = ["TOLLS"]
            body["routeModifiers"] = {
                "avoidTolls": avoid_tolls,
                "avoidHighways": avoid_highways,
                "vehicleInfo": {"emissionType": "GASOLINE"},
            }
        fields = ROUTE_FIELDS + (["routes.polyline.encodedPolyline"] if include_polyline else [])
        data = await self._client.post(ROUTES_URL, body, field_mask=",".join(fields))
        routes = data.get("routes") or []
        if not routes:
            raise ProviderError(T.Errors.GOOGLE_ROUTE_NOT_FOUND)
        return [parse_route(r) for r in routes]

    async def matrix(
        self,
        origins: list[Waypoint],
        destinations: list[Waypoint],
        *,
        mode: TravelMode = "driving",
        departure_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        body = self._base_body(mode, departure_time)
        body.pop("units", None)
        body["origins"] = [{"waypoint": waypoint_body(w)} for w in origins]
        body["destinations"] = [{"waypoint": waypoint_body(w)} for w in destinations]
        data = await self._client.post(MATRIX_URL, body, field_mask=MATRIX_FIELDS)
        return data if isinstance(data, list) else []
