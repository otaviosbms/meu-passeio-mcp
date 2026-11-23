from datetime import date

from meu_passeio.modules.planner.schemas import ParsedBudget, TripRequest
from meu_passeio.modules.planner.validator import validate_plan
from meu_passeio.shared.schemas import CostEstimate, TripActivity, TripDay, TripPlan


def _plan(**overrides) -> TripPlan:
    base = {
        "destination": "Curitiba",
        "start_date": date(2027, 7, 10),
        "end_date": date(2027, 7, 11),
        "itinerary": [
            TripDay(
                day_number=1,
                date=date(2027, 7, 10),
                activities=[
                    TripActivity(
                        id="a1",
                        name="Parque",
                        place_id="osm:way:1",
                        start_time="09:00",
                        duration_minutes=120,
                    ),
                    TripActivity(id="a2", name="Almoço", start_time="12:00", duration_minutes=60),
                ],
            ),
            TripDay(
                day_number=2,
                date=date(2027, 7, 11),
                activities=[TripActivity(id="a3", name="Museu")],
            ),
        ],
    }
    base.update(overrides)
    return TripPlan(**base)


def _request(budget: float | None = None) -> TripRequest:
    return TripRequest(
        trip_type="weekend",
        destination="Curitiba",
        duration_days=2,
        budget=ParsedBudget(amount=budget) if budget is not None else None,
    )


def test_valid_plan():
    report = validate_plan(_plan(), _request(), {"osm:way:1"})
    assert report.valid, report.errors


def test_unknown_place_id_is_error():
    report = validate_plan(_plan(), _request(), set())
    assert any("osm:way:1" in e for e in report.errors)


def test_time_conflict_detected():
    plan = _plan()
    plan.itinerary[0].activities[1].start_time = "10:00"
    report = validate_plan(plan, _request(), {"osm:way:1"})
    assert any("Conflito" in e for e in report.errors)


def test_day_count_mismatch():
    plan = _plan(itinerary=_plan().itinerary[:1])
    report = validate_plan(plan, _request(), {"osm:way:1"})
    assert any("dia(s)" in e for e in report.errors)


def test_over_budget():
    plan = _plan(cost_estimates=[CostEstimate(category="food", amount=500)])
    report = validate_plan(plan, _request(budget=300), {"osm:way:1"})
    assert any("acima do orçamento" in e for e in report.errors)
