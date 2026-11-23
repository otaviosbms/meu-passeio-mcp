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
    assert "estimativa" in result.disclaimer.lower()


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


def test_trip_cost_separates_real_sources_from_assumptions():
    items = [
        CostItem(category="fuel", amount=146.53, source="anp"),
        CostItem(category="tolls", amount=48.6, source="google_routes_tolls"),
        CostItem(category="food", amount=70, quantity=2, per_person=True, source="google_maps"),
        CostItem(category="activities", amount=200, source="assumption"),
    ]
    result = estimate_trip_cost(items, travelers=2)
    by_source = {s.source: s.total for s in result.by_source}
    assert by_source == {
        "anp": 146.53,
        "assumption": 200,
        "google_maps": 280,
        "google_routes_tolls": 48.6,
    }
    assert result.assumed_share == pytest.approx(200 / 675.13, abs=0.01)
    assert result.notes == []  # < 30% suposições

    mostly_assumed = estimate_trip_cost([CostItem(category="food", amount=100)], travelers=1)
    assert mostly_assumed.assumed_share == 1.0 and mostly_assumed.notes
