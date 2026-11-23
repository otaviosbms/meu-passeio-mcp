import pytest

from meu_passeio.mcp_server.budget.calculator import (
    CostItem,
    calculate_budget_breakdown,
    calculate_fuel_cost,
    estimate_trip_cost,
)


def test_fuel_cost_round_trip():
    result = calculate_fuel_cost(320, 12, 6.1, round_trip=True)
    assert result.distance_km_total == 640
    assert result.liters == pytest.approx(53.33, abs=0.01)
    assert result.estimated_cost == pytest.approx(325.33, abs=0.01)
    assert "não é um preço real" in result.disclaimer


def test_fuel_cost_rejects_invalid_consumption():
    with pytest.raises(ValueError):
        calculate_fuel_cost(100, 0, 6)


def test_estimate_trip_cost_per_person_and_budget():
    items = [
        CostItem(category="food", amount=80, quantity=2, per_person=True),
        CostItem(category="activities", amount=50, per_person=True),
        CostItem(category="transport", amount=120),
    ]
    result = estimate_trip_cost(items, travelers=2, budget=600)
    totals = {c.category: c.total for c in result.by_category}
    assert totals == {"activities": 100, "food": 320, "transport": 120}
    assert result.total == 540
    assert result.remaining == 60
    assert result.within_budget is True


def test_budget_breakdown_excludes_category_and_renormalizes():
    result = calculate_budget_breakdown(
        1800, days=4, travelers=2, excluded_categories=["transport"]
    )
    assert {a.category for a in result.allocations} == {"food", "activities", "contingency"}
    assert sum(a.amount for a in result.allocations) == pytest.approx(1800)
    assert result.per_person_per_day == 225
