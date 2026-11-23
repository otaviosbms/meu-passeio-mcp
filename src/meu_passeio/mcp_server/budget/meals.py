"""Estimativa de custo de refeição a partir da faixa de preço real (priceRange) do Google.

Busca estabelecimentos bem avaliados da região para o tipo de refeição e calcula a mediana
do ponto médio das faixas de preço por pessoa. Sem dados suficientes, não estima.
"""

from __future__ import annotations

import statistics
from typing import Literal

from pydantic import BaseModel, Field

from meu_passeio.mcp_server.common.http import ProviderError
from meu_passeio.mcp_server.places import service as places
from meu_passeio.mcp_server.places.schemas import PriceRange
from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import budget as T
from meu_passeio.texts.places import ATTRIBUTION

MealType = Literal["breakfast", "lunch", "dinner", "snack", "quick"]
MIN_SAMPLES = 3
MAX_LISTED = 8

# Refeição -> (tipo do Google, termo de busca)
MEALS: dict[str, tuple[str, str]] = {
    "breakfast": ("cafe", "café da manhã"),
    "lunch": ("restaurant", "almoço"),
    "dinner": ("restaurant", "jantar"),
    "snack": ("cafe", "lanche café"),
    "quick": ("fast_food_restaurant", "lanchonete"),
}


class PricedPlace(BaseModel):
    name: str
    rating: float | None = None
    user_rating_count: int | None = None
    price_range: PriceRange | None = None
    price_level: str | None = None


class MealCostEstimate(BaseModel):
    meal: MealType
    per_person_median: float | None = Field(description=T.Fields.MEAL_MEDIAN)
    typical_min: float | None = Field(default=None, description=T.Fields.MEAL_TYPICAL_RANGE)
    typical_max: float | None = Field(default=None, description=T.Fields.MEAL_TYPICAL_RANGE)
    currency: str | None = None
    sample_size: int
    places_considered: int
    examples: list[PricedPlace] = Field(default_factory=list)
    price_level_counts: dict[str, int] = Field(default_factory=dict)
    source: str = "google_maps"
    attribution: str = ATTRIBUTION
    notes: list[str] = Field(default_factory=list)


def _midpoint(price: PriceRange) -> float | None:
    if price.min is None and price.max is None:
        return None
    if price.max is None:
        return price.min
    if price.min is None:
        return price.max
    return (price.min + price.max) / 2


async def estimate_meal_cost(
    *,
    meal: MealType,
    location: str | None,
    coordinates: Coordinates | None,
    cuisine: str | None,
    radius_km: float,
    min_rating: float,
) -> MealCostEstimate:
    provider = places.google()
    if provider is None:
        raise ProviderError(T.Errors.MEAL_NEEDS_GOOGLE)
    center, _ = await places.resolve_center(location, coordinates)
    included_type, term = MEALS[meal]
    query = " ".join(p for p in (cuisine, term, f"em {location}" if location else None) if p)
    found, _ = await provider.text_search(
        text_query=query,
        center=center,
        radius_km=radius_km,
        limit=20,
        included_type=included_type,
        min_rating=min_rating,
        min_reviews=20,
    )

    priced = [(p, _midpoint(p.price_range)) for p in found if p.price_range]
    priced = [(p, m) for p, m in priced if m is not None]
    currencies = {p.price_range.currency for p, _ in priced if p.price_range}
    level_counts: dict[str, int] = {}
    for p in found:
        if p.price_level:
            level_counts[p.price_level] = level_counts.get(p.price_level, 0) + 1

    examples = [
        PricedPlace(
            name=p.name,
            rating=p.rating,
            user_rating_count=p.user_rating_count,
            price_range=p.price_range,
            price_level=p.price_level,
        )
        for p, _ in priced[:MAX_LISTED]
    ]
    notes: list[str] = []
    if len(priced) < MIN_SAMPLES or len(currencies) > 1:
        notes.append(T.Notes.MEAL_INSUFFICIENT.format(count=len(priced)))
        return MealCostEstimate(
            meal=meal,
            per_person_median=None,
            sample_size=len(priced),
            places_considered=len(found),
            examples=examples,
            price_level_counts=level_counts,
            notes=notes,
        )

    values = sorted(m for _, m in priced)
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    notes.append(T.Notes.MEAL_METHOD)
    return MealCostEstimate(
        meal=meal,
        per_person_median=round(statistics.median(values), 2),
        typical_min=round(q1, 2),
        typical_max=round(q3, 2),
        currency=next(iter(currencies)),
        sample_size=len(values),
        places_considered=len(found),
        examples=examples,
        price_level_counts=level_counts,
        notes=notes,
    )
