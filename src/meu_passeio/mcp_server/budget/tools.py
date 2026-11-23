"""Tools de custos — preços reais (ANP, Google) e cálculos de orçamento.

Textos (descrições, notas, erros): meu_passeio/texts/budget.py
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from meu_passeio.mcp_server.budget import calculator, meals
from meu_passeio.mcp_server.budget.calculator import (
    BudgetBreakdownResult,
    CostItem,
    FuelCostResult,
    TripCostResult,
)
from meu_passeio.mcp_server.budget.currency import SOURCE as PTAX_SOURCE
from meu_passeio.mcp_server.budget.currency import ptax
from meu_passeio.mcp_server.budget.fuel import SOURCE as ANP_SOURCE
from meu_passeio.mcp_server.budget.fuel import FuelType, anp
from meu_passeio.mcp_server.budget.meals import MealCostEstimate, MealType
from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import budget as T

PURE = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
ONLINE = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

StateArg = Annotated[str, Field(min_length=2, max_length=2, description=T.Params.STATE)]
CityArg = Annotated[str | None, Field(description=T.Params.CITY)]
FuelArg = Annotated[FuelType, Field(description=T.Params.FUEL)]


class FuelPriceResult(BaseModel):
    fuel: FuelType
    state: str
    city: str | None
    level: str = Field(description=T.Fields.FUEL_LEVEL)
    average: float
    median: float
    minimum: float
    maximum: float
    stations: int = Field(description=T.Fields.FUEL_STATIONS)
    unit: str
    period_start: date
    period_end: date
    source: str = ANP_SOURCE
    notes: list[str] = Field(default_factory=list)


async def _fuel_price(fuel: FuelType, state: str, city: str | None) -> FuelPriceResult:
    stats, level, matched_city = await anp().lookup(fuel, state, city)
    notes = [T.Notes.ANP_SOURCE]
    if city and level != "municipality":
        notes.append(T.Notes.ANP_CITY_NOT_SURVEYED.format(city=city, level=T.LEVELS[level]))
    return FuelPriceResult(
        fuel=fuel,
        state=state.upper(),
        city=matched_city,
        level=level,
        average=stats.average,
        median=stats.median,
        minimum=stats.minimum,
        maximum=stats.maximum,
        stations=stats.stations,
        unit=stats.unit,
        period_start=stats.period_start,
        period_end=stats.period_end,
        notes=notes,
    )


@safe_tool
async def get_fuel_price(
    state: StateArg,
    city: CityArg = None,
    fuel: FuelArg = "gasolina",
) -> FuelPriceResult:
    return await _fuel_price(fuel, state, city)


@safe_tool
async def calculate_fuel_cost(
    distance_km: Annotated[float, Field(ge=0, description=T.Params.DISTANCE_KM)],
    vehicle_consumption_km_per_liter: Annotated[
        float, Field(gt=0, description=T.Params.CONSUMPTION)
    ] = 12.0,
    fuel_price_per_liter: Annotated[
        float | None, Field(ge=0, description=T.Params.FUEL_PRICE)
    ] = None,
    state: Annotated[
        str | None, Field(min_length=2, max_length=2, description=T.Params.STATE)
    ] = None,
    city: CityArg = None,
    fuel: FuelArg = "gasolina",
    round_trip: bool = True,
) -> FuelCostResult:
    notes: list[str] = []
    source = "user"
    if fuel_price_per_liter is None:
        if not state:
            raise ValueError(T.Errors.FUEL_PRICE_OR_STATE)
        price = await _fuel_price(fuel, state, city)
        fuel_price_per_liter = price.average
        source = ANP_SOURCE
        notes = [
            T.Notes.FUEL_PRICE_FROM_ANP.format(
                price=f"{price.average:.2f}".replace(".", ","),
                level=T.LEVELS[price.level],
                start=price.period_start.strftime("%d/%m"),
                end=price.period_end.strftime("%d/%m/%Y"),
            ),
            *price.notes[1:],
        ]
    notes.append(T.Notes.CONSUMPTION_ASSUMPTION.format(km_l=vehicle_consumption_km_per_liter))
    result = calculator.calculate_fuel_cost(
        distance_km,
        vehicle_consumption_km_per_liter,
        fuel_price_per_liter,
        round_trip,
        price_source=source,
    )
    result.notes = notes
    return result


@safe_tool
async def estimate_meal_cost(
    meal: Annotated[MealType, Field(description=T.Params.MEAL)],
    location: Annotated[str | None, Field(description=T.Params.LOCATION)] = None,
    coordinates: Annotated[Coordinates | None, Field(description=T.Params.COORDINATES)] = None,
    cuisine: Annotated[str | None, Field(description=T.Params.CUISINE)] = None,
    radius_km: Annotated[float, Field(ge=0.5, le=50, description=T.Params.RADIUS_KM)] = 5,
    min_rating: Annotated[float, Field(ge=1, le=5, description=T.Params.MIN_RATING)] = 4.0,
) -> MealCostEstimate:
    return await meals.estimate_meal_cost(
        meal=meal,
        location=location,
        coordinates=coordinates,
        cuisine=cuisine,
        radius_km=radius_km,
        min_rating=min_rating,
    )


@safe_tool
async def estimate_trip_cost(
    items: Annotated[list[CostItem], Field(min_length=1, max_length=200)],
    travelers: Annotated[int, Field(ge=1, le=50)] = 1,
    budget: Annotated[float | None, Field(ge=0, description=T.Params.BUDGET)] = None,
) -> TripCostResult:
    return calculator.estimate_trip_cost(items, travelers, budget)


@safe_tool
async def calculate_budget_breakdown(
    total_budget: Annotated[float, Field(ge=0)],
    days: Annotated[int, Field(ge=1, le=60)],
    travelers: Annotated[int, Field(ge=1, le=50)] = 1,
    weights: Annotated[dict[str, float] | None, Field(description=T.Params.WEIGHTS)] = None,
    excluded_categories: Annotated[
        list[str] | None, Field(description=T.Params.EXCLUDED_CATEGORIES)
    ] = None,
) -> BudgetBreakdownResult:
    return calculator.calculate_budget_breakdown(
        total_budget, days, travelers, weights, excluded_categories
    )


class CurrencyConversion(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    converted: float
    rate: float = Field(description=T.Fields.RATE)
    quote_date: date = Field(description=T.Fields.QUOTE_DATE)
    quotes: dict[str, float] = Field(description=T.Fields.QUOTES)
    source: str = PTAX_SOURCE
    notes: list[str] = Field(default_factory=list)


@safe_tool
async def convert_currency(
    amount: Annotated[float, Field(ge=0, description=T.Params.AMOUNT)],
    from_currency: Annotated[
        str, Field(min_length=3, max_length=3, description=T.Params.FROM_CURRENCY)
    ],
    to_currency: Annotated[
        str, Field(min_length=3, max_length=3, description=T.Params.TO_CURRENCY)
    ] = "BRL",
    on_date: Annotated[date | None, Field(description=T.Params.QUOTE_ON)] = None,
) -> CurrencyConversion:
    source_code, target_code = from_currency.upper(), to_currency.upper()
    if source_code == target_code:
        raise ValueError(T.Errors.SAME_CURRENCY)
    day = min(on_date or date.today(), date.today())
    client = ptax()
    # R$ por unidade de cada moeda (BRL = 1)
    quotes: dict[str, float] = {}
    quote_dates: list[date] = []
    for code in {source_code, target_code} - {"BRL"}:
        quote = await client.closing_quote(code, day)
        quotes[code] = quote.sell
        quote_dates.append(quote.quoted_at.date())
    brl_per_source = quotes.get(source_code, 1.0)
    brl_per_target = quotes.get(target_code, 1.0)
    rate = brl_per_source / brl_per_target
    notes = [T.Notes.PTAX_REFERENCE]
    if on_date and on_date > date.today():
        notes.append(T.Notes.FUTURE_DATE_USES_LATEST)
    return CurrencyConversion(
        amount=amount,
        from_currency=source_code,
        to_currency=target_code,
        converted=round(amount * rate, 2),
        rate=round(rate, 6),
        quote_date=min(quote_dates),
        quotes={code: round(value, 4) for code, value in quotes.items()},
        notes=notes,
    )


def register(mcp: MCPServer) -> None:
    mcp.add_tool(convert_currency, description=T.Tools.CONVERT_CURRENCY, annotations=ONLINE)
    mcp.add_tool(get_fuel_price, description=T.Tools.GET_FUEL_PRICE, annotations=ONLINE)
    mcp.add_tool(calculate_fuel_cost, description=T.Tools.CALCULATE_FUEL_COST, annotations=ONLINE)
    mcp.add_tool(estimate_meal_cost, description=T.Tools.ESTIMATE_MEAL_COST, annotations=ONLINE)
    mcp.add_tool(estimate_trip_cost, description=T.Tools.ESTIMATE_TRIP_COST, annotations=PURE)
    mcp.add_tool(
        calculate_budget_breakdown,
        description=T.Tools.CALCULATE_BUDGET_BREAKDOWN,
        annotations=PURE,
    )
