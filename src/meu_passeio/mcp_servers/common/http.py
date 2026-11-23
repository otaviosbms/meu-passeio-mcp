"""Utilitários compartilhados pelos MCP Servers que chamam provedores HTTP externos."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Provedores públicos (Nominatim/Overpass/OSRM) exigem um User-Agent identificável.
# Usamos um nome genérico; em produção configure MEU_PASSEIO_HTTP_USER_AGENT com um contato
# próprio, conforme as políticas de uso do Nominatim/Overpass.
DEFAULT_USER_AGENT = "mcp-trip-planner/0.1"


class ProviderError(RuntimeError):
    """Erro de provedor externo com mensagem segura (sem tokens/URLs com segredos)."""


def build_client(timeout: float = 15.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": os.getenv("MEU_PASSEIO_HTTP_USER_AGENT", DEFAULT_USER_AGENT)},
        follow_redirects=True,
    )


async def get_json(
    client: httpx.AsyncClient, url: str, *, params: dict[str, Any] | None = None, provider: str
) -> Any:
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as exc:
        raise ProviderError(f"Provedor '{provider}' não respondeu a tempo.") from exc
    except httpx.HTTPStatusError as exc:
        raise ProviderError(
            f"Provedor '{provider}' retornou HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError(f"Falha ao consultar o provedor '{provider}'.") from exc


async def post_form_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    data: dict[str, Any],
    provider: str,
    timeout: float | None = None,
) -> Any:
    try:
        if timeout is not None:
            response = await client.post(url, data=data, timeout=timeout)
        else:
            response = await client.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as exc:
        raise ProviderError(f"Provedor '{provider}' não respondeu a tempo.") from exc
    except httpx.HTTPStatusError as exc:
        raise ProviderError(
            f"Provedor '{provider}' retornou HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError(f"Falha ao consultar o provedor '{provider}'.") from exc
