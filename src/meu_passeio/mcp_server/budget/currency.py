"""Câmbio oficial pela PTAX do Banco Central (API Olinda, dados abertos, sem chave).

A PTAX é a taxa de referência do BC (R$ por unidade da moeda). Usamos o boletim de
fechamento mais recente até a data pedida (fins de semana e feriados não têm cotação).
Conversões entre duas moedas estrangeiras passam pelo real (taxa cruzada).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from meu_passeio.mcp_server.common.http import ProviderError, build_client, get_json
from meu_passeio.texts import budget as T

BASE_URL = os.getenv(
    "BCB_PTAX_URL", "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
)
SOURCE = "bcb_ptax"
LOOKBACK_DAYS = 10
KEEP_QUOTES = "'"  # aspas simples ficam literais nos parâmetros OData


@dataclass
class Quote:
    currency: str
    buy: float  # cotacaoCompra (R$ por unidade)
    sell: float  # cotacaoVenda (R$ por unidade)
    quoted_at: datetime


def _bcb_date(value: date) -> str:
    return value.strftime("%m-%d-%Y")  # a API usa MM-DD-AAAA


def _odata_url(path: str, params: dict[str, str]) -> str:
    """A API Olinda exige '@' e '$' literais nos nomes e espaços como %20 (sem '+')."""
    query = "&".join(f"{key}={quote(value, safe=KEEP_QUOTES)}" for key, value in params.items())
    return f"{BASE_URL}/{path}?{query}"


class PtaxClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or build_client(timeout=20.0)
        self._currencies: dict[str, str] | None = None

    async def currencies(self) -> dict[str, str]:
        if self._currencies is None:
            data = await get_json(
                self._client, _odata_url("Moedas", {"$format": "json"}), provider=SOURCE
            )
            self._currencies = {
                item["simbolo"]: item.get("nomeFormatado", item["simbolo"])
                for item in data.get("value", [])
            }
        return self._currencies

    async def closing_quote(self, currency: str, on: date) -> Quote:
        currency = currency.upper()
        known = await self.currencies()
        if currency not in known:
            raise ProviderError(
                T.Errors.UNKNOWN_CURRENCY.format(
                    currency=currency, available=", ".join(sorted(known))
                )
            )
        start = on - timedelta(days=LOOKBACK_DAYS)
        url = _odata_url(
            "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,"
            "dataFinalCotacao=@dataFinalCotacao)",
            {
                "@moeda": f"'{currency}'",
                "@dataInicial": f"'{_bcb_date(start)}'",
                "@dataFinalCotacao": f"'{_bcb_date(on)}'",
                "$filter": "tipoBoletim eq 'Fechamento'",
                "$format": "json",
            },
        )
        data: dict[str, Any] = await get_json(self._client, url, provider=SOURCE)
        values = data.get("value") or []
        if not values:
            raise ProviderError(T.Errors.NO_QUOTE.format(currency=currency, date=on.isoformat()))
        latest = max(values, key=lambda v: v["dataHoraCotacao"])
        return Quote(
            currency=currency,
            buy=float(latest["cotacaoCompra"]),
            sell=float(latest["cotacaoVenda"]),
            quoted_at=datetime.fromisoformat(latest["dataHoraCotacao"][:19]),
        )


_ptax: PtaxClient | None = None


def ptax() -> PtaxClient:
    global _ptax
    if _ptax is None:
        _ptax = PtaxClient()
    return _ptax
