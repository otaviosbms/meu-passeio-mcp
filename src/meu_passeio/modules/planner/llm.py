"""Camada fina sobre o SDK da Anthropic (Claude) usada pelos nós do planner.

- Modelo padrão: claude-opus-5-5 com thinking adaptativo (padrão do modelo) e effort configurável.
- Fallback server-side em caso de recusa (``fallbacks="default"``), habilitado por padrão.
- A API key é lida pelo SDK do ambiente (ANTHROPIC_API_KEY) e nunca entra no prompt.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel

from meu_passeio.core.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class PlannerLLMError(RuntimeError):
    """Falha ao obter resposta utilizável do LLM (recusa, limite de tokens, API)."""


class LLMClient:
    def __init__(self, settings: Settings, client: anthropic.AsyncAnthropic | None = None) -> None:
        self._settings = settings
        self._client = client or anthropic.AsyncAnthropic()

    def _common(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self._settings.llm_model,
            "max_tokens": self._settings.llm_max_tokens,
            "output_config": {"effort": self._settings.llm_effort},
        }
        if self._settings.llm_enable_fallbacks:
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
        return params

    @staticmethod
    def _check_stop(response: Any) -> None:
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise PlannerLLMError(f"O modelo recusou a solicitação (categoria: {category}).")
        if response.stop_reason == "max_tokens":
            raise PlannerLLMError("Resposta do modelo truncada (max_tokens).")

    async def create(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> Any:
        try:
            response = await self._client.beta.messages.create(
                **self._common(), system=system, messages=messages, tools=tools
            )
        except anthropic.APIStatusError as exc:
            raise PlannerLLMError(f"Erro da API do Claude (HTTP {exc.status_code}).") from exc
        except anthropic.APIConnectionError as exc:
            raise PlannerLLMError("Falha de conexão com a API do Claude.") from exc
        self._check_stop(response)
        return response

    async def parse(
        self, *, system: str, messages: list[dict[str, Any]], output_format: type[T]
    ) -> T:
        try:
            response = await self._client.beta.messages.parse(
                **self._common(), system=system, messages=messages, output_format=output_format
            )
        except anthropic.APIStatusError as exc:
            raise PlannerLLMError(f"Erro da API do Claude (HTTP {exc.status_code}).") from exc
        except anthropic.APIConnectionError as exc:
            raise PlannerLLMError("Falha de conexão com a API do Claude.") from exc
        self._check_stop(response)
        parsed = response.parsed_output
        if parsed is None:
            raise PlannerLLMError("O modelo não retornou uma saída estruturada válida.")
        return parsed
