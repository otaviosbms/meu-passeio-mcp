"""Verifica se um lugar está aberto num horário, a partir dos ``periods`` do Google Places.

Formato do Google: ``{"open": {"day": 0-6, "hour": h, "minute": m}, "close": {...}}``,
com ``day`` 0 = domingo. Um único período sem ``close`` significa aberto 24 horas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from meu_passeio.texts import places as T

MINUTES_PER_WEEK = 7 * 24 * 60


@dataclass
class OpeningStatus:
    is_open: bool | None
    opens_at: str | None = None
    closes_at: str | None = None


def _minute_of_week(point: dict[str, Any]) -> int:
    return (
        int(point.get("day", 0)) * 1440
        + int(point.get("hour", 0)) * 60
        + int(point.get("minute", 0))
    )


def _label(minute_of_week: int) -> str:
    minute_of_week %= MINUTES_PER_WEEK
    day, rest = divmod(minute_of_week, 1440)
    return f"{T.WEEKDAYS[day]} {rest // 60:02d}:{rest % 60:02d}"


def opening_status(periods: list[dict[str, Any]] | None, at: datetime) -> OpeningStatus:
    """``at`` é o horário local do lugar (sem fuso)."""
    if not periods:
        return OpeningStatus(is_open=None)
    google_weekday = (at.weekday() + 1) % 7  # Python: segunda = 0; Google: domingo = 0
    now = google_weekday * 1440 + at.hour * 60 + at.minute

    intervals: list[tuple[int, int]] = []
    for period in periods:
        start_point, end_point = period.get("open"), period.get("close")
        if not start_point:
            continue
        if not end_point:  # aberto 24 horas
            return OpeningStatus(is_open=True)
        start, end = _minute_of_week(start_point), _minute_of_week(end_point)
        if end <= start:
            end += MINUTES_PER_WEEK
        intervals.append((start, end))

    for start, end in intervals:
        for candidate in (now, now + MINUTES_PER_WEEK):
            if start <= candidate < end:
                return OpeningStatus(is_open=True, closes_at=_label(end))

    if not intervals:
        return OpeningStatus(is_open=None)
    next_start = min(intervals, key=lambda iv: (iv[0] - now) % MINUTES_PER_WEEK)[0]
    return OpeningStatus(is_open=False, opens_at=_label(next_start))
