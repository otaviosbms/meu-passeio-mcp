"""Budget MCP Server — estimativas e cálculos determinísticos (sem API externa).

Execução (stdio):  python -m meu_passeio.mcp_servers.budget
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from meu_passeio.core.logging import configure_logging
from meu_passeio.mcp_servers.budget import calculator
from meu_passeio.mcp_servers.budget.calculator import (
    BudgetBreakdownResult,
    CostItem,
    FuelCostResult,
    TripCostResult,
)
from meu_passeio.mcp_servers.common.errors import safe_tool

mcp = MCPServer(
    name="meu-passeio-budget",
    instructions="Cálculos de orçamento. Resultados são estimativas, nunca preços reais.",
)
PURE = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


@mcp.tool(annotations=PURE)
@safe_tool
async def calculate_fuel_cost(
    distance_km: Annotated[float, Field(ge=0, description="Distância de um trecho, em km")],
    vehicle_consumption_km_per_liter: Annotated[float, Field(gt=0)] = 12.0,
    fuel_price_per_liter: Annotated[float, Field(ge=0, description="Preço do litro em BRL")] = 6.0,
    round_trip: bool = True,
) -> FuelCostResult:
    """Estima o custo de combustível a partir de distância, consumo do veículo e preço do litro."""
    return calculator.calculate_fuel_cost(
        distance_km, vehicle_consumption_km_per_liter, fuel_price_per_liter, round_trip
    )


@mcp.tool(annotations=PURE)
@safe_tool
async def estimate_trip_cost(
    items: Annotated[list[CostItem], Field(min_length=1, max_length=200)],
    travelers: Annotated[int, Field(ge=1, le=50)] = 1,
    budget: Annotated[float | None, Field(ge=0, description="Orçamento para comparar")] = None,
) -> TripCostResult:
    """Consolida custos (atividades, alimentação, deslocamentos, hospedagem) e compara ao orçamento."""
    return calculator.estimate_trip_cost(items, travelers, budget)


@mcp.tool(annotations=PURE)
@safe_tool
async def calculate_budget_breakdown(
    total_budget: Annotated[float, Field(ge=0)],
    days: Annotated[int, Field(ge=1, le=60)],
    travelers: Annotated[int, Field(ge=1, le=50)] = 1,
    weights: Annotated[
        dict[str, float] | None,
        Field(
            description="Pesos por categoria (padrão: food 40, activities 30, transport 20, contingency 10)"
        ),
    ] = None,
    excluded_categories: Annotated[
        list[str] | None, Field(description="Categorias a excluir")
    ] = None,
) -> BudgetBreakdownResult:
    """Distribui um orçamento por categorias e por dia, indicando valores por pessoa."""
    return calculator.calculate_budget_breakdown(
        total_budget, days, travelers, weights, excluded_categories
    )


def main() -> None:
    configure_logging()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
