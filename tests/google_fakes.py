"""Simulador do Google Maps (Places API (New) e Routes API) para os testes."""

from __future__ import annotations

import json
from typing import Any

import httpx

from meu_passeio.shared.schemas import Coordinates

FAKE_KEY = "test-key-123"
CENTER = Coordinates(latitude=-25.4284, longitude=-49.2733)


def _place(pid: str, name: str, rating: float, count: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": pid,
        "displayName": {"text": name},
        "formattedAddress": f"{name}, Curitiba - PR",
        "location": {"latitude": -25.43, "longitude": -49.27},
        "rating": rating,
        "userRatingCount": count,
        "primaryType": "park",
        "primaryTypeDisplayName": {"text": "Parque"},
        "businessStatus": "OPERATIONAL",
        "googleMapsUri": f"https://maps.google.com/?cid={pid}",
        **extra,
    }


class FakeGoogle:
    """Registra as requisições e devolve respostas por endpoint."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.responses: dict[str, Any] = {}
        self.status: dict[str, int] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        for key, payload in self.responses.items():
            if path.endswith(key):
                return httpx.Response(self.status.get(key, 200), json=payload)
        return httpx.Response(404, json={"error": {"status": "NOT_FOUND", "message": path}})

    def bodies(self, suffix: str) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests if r.url.path.endswith(suffix)]
