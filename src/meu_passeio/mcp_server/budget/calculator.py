"""Cálculos determinísticos de orçamento — sem I/O, fáceis de testar.

Os cálculos usam os valores informados. Cada item de custo declara sua fonte (Google, ANP,
pedágios, usuário ou suposição), e o resultado separa o que é dado real do que é suposição.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from meu_passeio.texts import budget as T

DISCLAIMER = T.DISCLAIMER


CostSource = Literal["google_maps", "anp", "google_routes_tolls", "user", "assumption"]
REAL_SOURCES = {"google_maps", "anp", "google_routes_tolls", "user"}
ASSUMPTION_WARNING_SHARE = 0.3


class FuelCostResult(BaseModel):
    distance_km_total: float
    liters: float
    estimated_cost: float
    currency: str = "BRL"
    parameters: dict[str, float | bool | str]
    price_source: str | None = Field(default=None, description=T.Fields.PRICE_SOURCE)
    formula: str
    notes: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


class CostItem(BaseModel):
    category: str = Field(description=T.Fields.CATEGORY)
    description: str | None = None
    amount: float = Field(ge=0, description=T.Fields.AMOUNT)
    quantity: float = Field(default=1, ge=0)
    per_person: bool = Field(default=False, description=T.Fields.PER_PERSON)
    source: CostSource = Field(default="assumption", description=T.Fields.ITEM_SOURCE)


class CategoryTotal(BaseModel):
    category: str
    total: float


class SourceTotal(BaseModel):
    source: CostSource
    total: float


class TripCostResult(BaseModel):
    travelers: int
    by_category: list[CategoryTotal]
    by_source: list[SourceTotal]
    total: float
    per_person: float
    assumed_share: float = Field(description=T.Fields.ASSUMED_SHARE)
    currency: str = "BRL"
    budget: float | None = None
    remaining: float | None = None
    within_budget: bool | None = None
    notes: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


class BudgetAllocation(BaseModel):
    category: str
    percentage: float
    amount: float
    per_day: float


class BudgetBreakdownResult(BaseModel):
    total_budget: float
    days: int
    travelers: int
    allocations: list[BudgetAllocation]
    per_person_per_day: float
    currency: str = "BRL"
    notes: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


DEFAULT_WEIGHTS: dict[str, float] = {
    "food": 0.40,
    "activities": 0.30,
    "transport": 0.20,
    "contingency": 0.10,
}


def _r(value: float) -> float:
    return round(value + 0.0, 2)


def calculate_fuel_cost(
    distance_km: float,
    consumption_km_per_liter: float,
    fuel_price_per_liter: float,
    round_trip: bool = False,
    *,
    price_source: str | None = None,
) -> FuelCostResult:
    if distance_km < 0:
        raise ValueError(T.Errors.NEGATIVE_DISTANCE)
    if consumption_km_per_liter <= 0:
        raise ValueError(T.Errors.INVALID_CONSUMPTION)
    if fuel_price_per_liter < 0:
        raise ValueError(T.Errors.NEGATIVE_FUEL_PRICE)
    total_km = distance_km * (2 if round_trip else 1)
    liters = total_km / consumption_km_per_liter
    return FuelCostResult(
        distance_km_total=_r(total_km),
        liters=_r(liters),
        estimated_cost=_r(liters * fuel_price_per_liter),
        parameters={
            "distance_km": distance_km,
            "consumption_km_per_liter": consumption_km_per_liter,
            "fuel_price_per_liter": fuel_price_per_liter,
            "round_trip": round_trip,
        },
        price_source=price_source,
        formula=T.FUEL_FORMULA,
    )


def estimate_trip_cost(
    items: list[CostItem], travelers: int = 1, budget: float | None = None
) -> TripCostResult:
    if travelers < 1:
        raise ValueError(T.Errors.INVALID_TRAVELERS)
    totals: dict[str, float] = {}
    by_source: dict[str, float] = {}
    for item in items:
        value = item.amount * item.quantity * (travelers if item.per_person else 1)
        totals[item.category] = totals.get(item.category, 0.0) + value
        by_source[item.source] = by_source.get(item.source, 0.0) + value
    total = sum(totals.values())
    assumed = sum(v for k, v in by_source.items() if k not in REAL_SOURCES)
    share = assumed / total if total else 0.0
    notes = (
        [T.Notes.HIGH_ASSUMED_SHARE.format(pct=round(share * 100))]
        if share > ASSUMPTION_WARNING_SHARE
        else []
    )
    remaining = _r(budget - total) if budget is not None else None
    return TripCostResult(
        travelers=travelers,
        by_category=[CategoryTotal(category=k, total=_r(v)) for k, v in sorted(totals.items())],
        by_source=[SourceTotal(source=k, total=_r(v)) for k, v in sorted(by_source.items())],  # type: ignore[arg-type]
        total=_r(total),
        per_person=_r(total / travelers),
        assumed_share=_r(share),
        budget=budget,
        remaining=remaining,
        within_budget=(remaining >= 0) if remaining is not None else None,
        notes=notes,
    )


def calculate_budget_breakdown(
    total_budget: float,
    days: int,
    travelers: int = 1,
    weights: dict[str, float] | None = None,
    excluded_categories: list[str] | None = None,
) -> BudgetBreakdownResult:
    if total_budget < 0:
        raise ValueError(T.Errors.NEGATIVE_BUDGET)
    if days < 1 or travelers < 1:
        raise ValueError(T.Errors.INVALID_DAYS_OR_TRAVELERS)
    raw = dict(weights or DEFAULT_WEIGHTS)
    notes: list[str] = []
    for excluded in excluded_categories or []:
        if raw.pop(excluded, None) is not None:
            notes.append(T.Notes.CATEGORY_EXCLUDED.format(category=excluded))
    if not raw or sum(raw.values()) <= 0:
        raise ValueError(T.Errors.INVALID_WEIGHTS)
    weight_sum = sum(raw.values())
    allocations = [
        BudgetAllocation(
            category=cat,
            percentage=_r(w / weight_sum * 100),
            amount=_r(total_budget * w / weight_sum),
            per_day=_r(total_budget * w / weight_sum / days),
        )
        for cat, w in raw.items()
    ]
    return BudgetBreakdownResult(
        total_budget=total_budget,
        days=days,
        travelers=travelers,
        allocations=allocations,
        per_person_per_day=_r(total_budget / days / travelers),
        notes=notes,
    )
