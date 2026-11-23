"""Tools de orçamento — estimativas e cálculos determinísticos (sem API externa).

Textos (descrições, notas, erros): meu_passeio/texts/budget.py
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from meu_passeio.mcp_server.budget import calculator
from meu_passeio.mcp_server.budget.calculator import (
    BudgetBreakdownResult,
    CostItem,
    FuelCostResult,
    TripCostResult,
)
from meu_passeio.mcp_server.common.errors import safe_tool
from meu_passeio.texts import budget as T

PURE = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


@safe_tool
async def calculate_fuel_cost(
    distance_km: Annotated[float, Field(ge=0, description=T.Params.DISTANCE_KM)],
    vehicle_consumption_km_per_liter: Annotated[float, Field(gt=0)] = 12.0,
    fuel_price_per_liter: Annotated[float, Field(ge=0, description=T.Params.FUEL_PRICE)] = 6.0,
    round_trip: bool = True,
) -> FuelCostResult:
    return calculator.calculate_fuel_cost(
        distance_km, vehicle_consumption_km_per_liter, fuel_price_per_liter, round_trip
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


def register(mcp: MCPServer) -> None:
    mcp.add_tool(calculate_fuel_cost, description=T.Tools.CALCULATE_FUEL_COST, annotations=PURE)
    mcp.add_tool(estimate_trip_cost, description=T.Tools.ESTIMATE_TRIP_COST, annotations=PURE)
    mcp.add_tool(
        calculate_budget_breakdown,
        description=T.Tools.CALCULATE_BUDGET_BREAKDOWN,
        annotations=PURE,
    )
