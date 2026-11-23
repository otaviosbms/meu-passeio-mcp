"""Validator determinístico do itinerário (orçamento, datas, consistência e dados)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from meu_passeio.modules.planner.schemas import TripRequest
from meu_passeio.shared.schemas import TripPlan


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)  # bloqueiam: pedem replanejamento
    warnings: list[str] = field(default_factory=list)  # informativos

    @property
    def valid(self) -> bool:
        return not self.errors


def _minutes(hhmm: str) -> int | None:
    try:
        hours, minutes = hhmm.split(":")
        return int(hours) * 60 + int(minutes)
    except (ValueError, AttributeError):
        return None


def validate_plan(
    plan: TripPlan, request: TripRequest | None, known_place_ids: set[str]
) -> ValidationReport:
    report = ValidationReport()

    if not plan.itinerary:
        report.errors.append("O itinerário está vazio.")
        return report

    # Dias sequenciais e coerentes com as datas
    numbers = [d.day_number for d in plan.itinerary]
    if numbers != list(range(1, len(numbers) + 1)):
        report.errors.append("day_number deve ser sequencial a partir de 1.")

    expected_days = None
    if plan.start_date and plan.end_date:
        if plan.end_date < plan.start_date:
            report.errors.append("end_date anterior a start_date.")
        else:
            expected_days = (plan.end_date - plan.start_date).days + 1
            for day in plan.itinerary:
                if day.date and not (plan.start_date <= day.date <= plan.end_date):
                    report.errors.append(f"Dia {day.day_number} fora do período da viagem.")
                expected = plan.start_date + timedelta(days=day.day_number - 1)
                if day.date and day.date != expected:
                    report.warnings.append(
                        f"Dia {day.day_number} com data {day.date} (esperado {expected})."
                    )
    elif request and request.duration_days:
        expected_days = request.duration_days
    if expected_days and len(plan.itinerary) != expected_days:
        report.errors.append(
            f"O roteiro tem {len(plan.itinerary)} dia(s), mas a viagem tem {expected_days}."
        )

    # Atividades: conflitos de horário e lugares rastreáveis
    for day in plan.itinerary:
        if not day.activities:
            report.warnings.append(f"Dia {day.day_number} sem atividades.")
        slots: list[tuple[int, int, str]] = []
        for activity in day.activities:
            if activity.place_id and activity.place_id not in known_place_ids:
                report.errors.append(
                    f"Atividade '{activity.name}' usa place_id '{activity.place_id}' que não veio "
                    "das ferramentas."
                )
            start = _minutes(activity.start_time) if activity.start_time else None
            if start is not None and activity.duration_minutes:
                slots.append((start, start + activity.duration_minutes, activity.name))
        slots.sort()
        for (_, end_a, name_a), (start_b, _, name_b) in zip(slots, slots[1:], strict=False):
            if start_b < end_a:
                report.errors.append(
                    f"Conflito de horário no dia {day.day_number}: '{name_a}' e '{name_b}'."
                )

    # Orçamento
    budget = (
        plan.budget.total
        if plan.budget
        else (request.budget.amount if request and request.budget else None)
    )
    excluded = set(
        (plan.budget.excluded_categories if plan.budget else [])
        or (request.budget.excluded_categories if request and request.budget else [])
    )
    if budget is not None:
        if plan.cost_estimates:
            total = sum(c.amount for c in plan.cost_estimates if c.category not in excluded)
        else:
            total = sum(a.estimated_cost or 0 for d in plan.itinerary for a in d.activities)
        if total > budget * 1.05:
            report.errors.append(
                f"Custo estimado (R$ {total:.2f}) acima do orçamento (R$ {budget:.2f})."
            )
        elif total > budget:
            report.warnings.append(
                f"Custo estimado (R$ {total:.2f}) ligeiramente acima do orçamento "
                f"(R$ {budget:.2f})."
            )

    return report
