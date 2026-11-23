"""Cliente HTTP do Google Maps Platform (Places API (New) e Routes API).

- A chave vai no header ``X-Goog-Api-Key`` (nunca na URL, nos logs ou nas respostas).
- Toda chamada envia um ``X-Goog-FieldMask`` mínimo: o Google cobra por campo solicitado.
- Erros do Google viram ``ProviderError`` com status e mensagem do provedor (sem a chave).
"""

from __future__ import annotations

from typing import Any

import httpx

from meu_passeio.core.config import get_settings
from meu_passeio.mcp_server.common.http import ProviderError, build_client
from meu_passeio.texts.common import ProviderErrors

PROVIDER = "google_maps"
MAX_ERROR_MESSAGE = 300


class GoogleMapsClient:
    def __init__(self, api_key: str, client: httpx.AsyncClient, *, language: str, region: str):
        self._api_key = api_key
        self._client = client
        self.language = language
        self.region = region

    def _headers(self, field_mask: str) -> dict[str, str]:
        return {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": field_mask,
            "Content-Type": "application/json",
        }

    async def post(self, url: str, body: dict[str, Any], *, field_mask: str) -> Any:
        return await self._request("POST", url, json=body, field_mask=field_mask)

    async def get(self, url: str, *, field_mask: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", url, params=params, field_mask=field_mask)

    async def _request(self, method: str, url: str, *, field_mask: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(
                method, url, headers=self._headers(field_mask), **kwargs
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(ProviderErrors.TIMEOUT.format(provider=PROVIDER)) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(ProviderErrors.REQUEST_FAILED.format(provider=PROVIDER)) from exc
        if response.status_code >= 400:
            raise ProviderError(_error_message(response))
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError(ProviderErrors.REQUEST_FAILED.format(provider=PROVIDER)) from exc


def _error_message(response: httpx.Response) -> str:
    status, message = str(response.status_code), ""
    try:
        error = response.json().get("error", {})
        status = error.get("status") or status
        message = (error.get("message") or "")[:MAX_ERROR_MESSAGE]
    except (ValueError, AttributeError):
        pass
    return ProviderErrors.GOOGLE_ERROR.format(status=status, message=message).strip()


def money_to_float(money: dict[str, Any] | None) -> float | None:
    """Converte google.type.Money ({currencyCode, units, nanos}) em float."""
    if not money:
        return None
    return int(money.get("units") or 0) + int(money.get("nanos") or 0) / 1e9


def duration_seconds(value: str | None) -> int | None:
    """Converte durações do Google no formato '123s' em segundos."""
    if not value:
        return None
    return round(float(value.rstrip("s")))


_client: GoogleMapsClient | None = None


def get_google_client() -> GoogleMapsClient | None:
    """Cliente compartilhado; ``None`` quando GOOGLE_MAPS_API_KEY não está configurada."""
    global _client
    if _client is None:
        settings = get_settings()
        if (
            settings.google_maps_api_key is None
            or not settings.google_maps_api_key.get_secret_value()
        ):
            return None
        _client = GoogleMapsClient(
            settings.google_maps_api_key.get_secret_value(),
            build_client(timeout=settings.google_timeout_seconds),
            language=settings.google_language,
            region=settings.google_region,
        )
    return _client
