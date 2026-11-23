"""Preços de combustível da ANP (Levantamento de Preços de Combustíveis — dados abertos).

Fonte: arquivos "últimas 4 semanas" da série histórica da ANP, com o preço de venda por
posto pesquisado (CSV ``;``, vírgula decimal, datas dd/mm/aaaa). A pesquisa cobre cerca de
400 municípios; para os demais, devolvemos a média do estado, avisando.

Os arquivos são baixados sob demanda e mantidos em memória por ``CACHE_TTL``.
"""

from __future__ import annotations

import asyncio
import csv
import io
import os
import statistics
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal

import httpx

from meu_passeio.mcp_server.common.http import ProviderError, build_client
from meu_passeio.texts import budget as T
from meu_passeio.texts.common import ProviderErrors

BASE_URL = os.getenv(
    "ANP_FUEL_BASE_URL",
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/qus",
)
FILES = {
    "gasolina-etanol": f"{BASE_URL}/ultimas-4-semanas-gasolina-etanol.csv",
    "diesel-gnv": f"{BASE_URL}/ultimas-4-semanas-diesel-gnv.csv",
}
CACHE_TTL = float(os.getenv("ANP_CACHE_TTL_SECONDS", str(12 * 3600)))
RECENT_DAYS = 14  # usa as coletas dos últimos 14 dias antes da mais recente
SOURCE = "anp"

FuelType = Literal["gasolina", "gasolina_aditivada", "etanol", "diesel", "diesel_s10", "gnv"]

PRODUCTS: dict[str, tuple[str, str]] = {
    "gasolina": ("gasolina-etanol", "GASOLINA"),
    "gasolina_aditivada": ("gasolina-etanol", "GASOLINA ADITIVADA"),
    "etanol": ("gasolina-etanol", "ETANOL"),
    "diesel": ("diesel-gnv", "DIESEL"),
    "diesel_s10": ("diesel-gnv", "DIESEL S10"),
    "gnv": ("diesel-gnv", "GNV"),
}


def normalize(text: str) -> str:
    """'Marília' -> 'MARILIA' (a ANP grava municípios em maiúsculas, sem acento)."""
    decomposed = unicodedata.normalize("NFKD", text.strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


@dataclass
class Sample:
    price: float
    collected: date


@dataclass
class Dataset:
    # (UF, MUNICIPIO, PRODUTO) -> amostras
    by_city: dict[tuple[str, str, str], list[Sample]] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)  # PRODUTO -> unidade (ex.: R$ / litro)
    loaded_at: float = 0.0


@dataclass
class PriceStats:
    average: float
    median: float
    minimum: float
    maximum: float
    stations: int
    period_start: date
    period_end: date
    unit: str


def parse_csv(text: str, dataset: Dataset) -> None:
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    for row in reader:
        try:
            price = float((row.get("Valor de Venda") or "").replace(",", "."))
            collected = datetime.strptime(row["Data da Coleta"], "%d/%m/%Y").date()
        except (ValueError, KeyError, TypeError):
            continue
        key = (
            normalize(row.get("Estado - Sigla") or ""),
            normalize(row.get("Municipio") or ""),
            normalize(row.get("Produto") or ""),
        )
        dataset.by_city.setdefault(key, []).append(Sample(price, collected))
        if row.get("Unidade de Medida"):
            dataset.units.setdefault(key[2], row["Unidade de Medida"].replace(" ", ""))


def summarize(samples: list[Sample], unit: str) -> PriceStats:
    latest = max(s.collected for s in samples)
    recent = [s for s in samples if s.collected >= latest - timedelta(days=RECENT_DAYS)]
    prices = [s.price for s in recent]
    return PriceStats(
        average=round(statistics.fmean(prices), 3),
        median=round(statistics.median(prices), 3),
        minimum=min(prices),
        maximum=max(prices),
        stations=len(prices),
        period_start=min(s.collected for s in recent),
        period_end=latest,
        unit=unit,
    )


class AnpFuelPrices:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or build_client(timeout=90.0)
        self._datasets: dict[str, Dataset] = {}
        self._lock = asyncio.Lock()

    async def _download(self, name: str) -> Dataset:
        try:
            response = await self._client.get(FILES[name])
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderError(ProviderErrors.TIMEOUT.format(provider=SOURCE)) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                ProviderErrors.HTTP_STATUS.format(provider=SOURCE, status=exc.response.status_code)
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(ProviderErrors.REQUEST_FAILED.format(provider=SOURCE)) from exc
        dataset = Dataset(loaded_at=time.monotonic())
        parse_csv(response.content.decode("utf-8-sig", errors="replace"), dataset)
        if not dataset.by_city:
            raise ProviderError(T.Errors.ANP_EMPTY)
        return dataset

    async def dataset(self, name: str) -> Dataset:
        async with self._lock:
            current = self._datasets.get(name)
            if current is None or time.monotonic() - current.loaded_at > CACHE_TTL:
                self._datasets[name] = await self._download(name)
            return self._datasets[name]

    async def lookup(
        self, fuel: FuelType, state: str, city: str | None
    ) -> tuple[PriceStats, Literal["municipality", "state", "national"], str | None]:
        """Retorna estatísticas e o nível usado (município, estado ou Brasil)."""
        file_name, product = PRODUCTS[fuel]
        data = await self.dataset(file_name)
        uf, product_key = normalize(state), normalize(product)
        unit = data.units.get(product_key, "R$/litro")
        if city:
            samples = data.by_city.get((uf, normalize(city), product_key))
            if samples:
                return summarize(samples, unit), "municipality", normalize(city)
        state_samples = [
            s
            for (u, _, p), items in data.by_city.items()
            if u == uf and p == product_key
            for s in items
        ]
        if state_samples:
            return summarize(state_samples, unit), "state", None
        national = [
            s for (_, _, p), items in data.by_city.items() if p == product_key for s in items
        ]
        if not national:
            raise ProviderError(T.Errors.FUEL_NOT_FOUND.format(fuel=fuel))
        return summarize(national, unit), "national", None


_anp: AnpFuelPrices | None = None


def anp() -> AnpFuelPrices:
    global _anp
    if _anp is None:
        _anp = AnpFuelPrices()
    return _anp
