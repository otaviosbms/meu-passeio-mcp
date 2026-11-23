"""Provider de rotas baseado em OSRM (routing.openstreetmap.de), sem API key.

OSRM calcula durações com base na malha viária — SEM trânsito em tempo real.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from meu_passeio.mcp_servers.common.http import ProviderError, get_json
from meu_passeio.shared.schemas import Coordinates, TravelMode
from meu_passeio.texts import maps as T

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://routing.openstreetmap.de")
_PROFILES: dict[str, str] = {
    "driving": "routed-car",
    "walking": "routed-foot",
    "cycling": "routed-bike",
}
SOURCE = "osrm"


def _coords(points: list[Coordinates]) -> str:
    return ";".join(f"{p.longitude:.6f},{p.latitude:.6f}" for p in points)


class OsrmProvider:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def _url(self, service: str, mode: TravelMode, points: list[Coordinates]) -> str:
        profile = _PROFILES[mode]
        return f"{OSRM_BASE_URL}/{profile}/{service}/v1/driving/{_coords(points)}"

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        data = await get_json(self._client, url, params=params, provider=SOURCE)
        if data.get("code") != "Ok":
            raise ProviderError(
                T.Errors.ROUTE_NOT_FOUND.format(code=data.get("code", T.Errors.UNKNOWN_CODE))
            )
        return data

    async def route(
        self, origin: Coordinates, destination: Coordinates, mode: TravelMode, polyline: bool
    ) -> dict[str, Any]:
        data = await self._get(
            self._url("route", mode, [origin, destination]),
            {"overview": "simplified" if polyline else "false", "geometries": "polyline"},
        )
        route = data["routes"][0]
        return {
            "distance_meters": round(route["distance"]),
            "duration_seconds": round(route["duration"]),
            "polyline": route.get("geometry") if polyline else None,
        }

    async def table(
        self, origins: list[Coordinates], destinations: list[Coordinates], mode: TravelMode
    ) -> dict[str, Any]:
        points = origins + destinations
        data = await self._get(
            self._url("table", mode, points),
            {
                "sources": ";".join(str(i) for i in range(len(origins))),
                "destinations": ";".join(
                    str(i) for i in range(len(origins), len(origins) + len(destinations))
                ),
                "annotations": "duration,distance",
            },
        )
        return {"durations": data.get("durations"), "distances": data.get("distances")}

    async def trip(
        self, stops: list[Coordinates], mode: TravelMode, roundtrip: bool
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"overview": "false", "roundtrip": str(roundtrip).lower()}
        if not roundtrip:
            params.update({"source": "first", "destination": "last"})
        data = await self._get(self._url("trip", mode, stops), params)
        waypoints = data["waypoints"]
        order = sorted(range(len(waypoints)), key=lambda i: waypoints[i]["waypoint_index"])
        trip = data["trips"][0]
        return {
            "order": order,
            "distance_meters": round(trip["distance"]),
            "duration_seconds": round(trip["duration"]),
        }
