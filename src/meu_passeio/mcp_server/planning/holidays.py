"""Feriados nacionais do Brasil calculados localmente (sem API).

Base legal: Leis 662/1949, 6.802/1980, 10.607/2002 e 14.759/2023 (Consciência Negra como
feriado nacional desde 2024). Carnaval, Quarta-feira de Cinzas e Corpus Christi são pontos
facultativos nacionais (feriado em muitos estados e municípios). Datas móveis seguem a Páscoa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from meu_passeio.texts import planning as T

CONSCIENCIA_NEGRA_SINCE = 2024


@dataclass(frozen=True)
class Holiday:
    date: date
    name: str
    kind: str  # "national" | "optional"


def easter(year: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def holidays_of_year(year: int) -> list[Holiday]:
    e = easter(year)
    names = T.HolidayNames
    items = [
        Holiday(date(year, 1, 1), names.NEW_YEAR, "national"),
        Holiday(e - timedelta(days=48), names.CARNIVAL_MONDAY, "optional"),
        Holiday(e - timedelta(days=47), names.CARNIVAL_TUESDAY, "optional"),
        Holiday(e - timedelta(days=46), names.ASH_WEDNESDAY, "optional"),
        Holiday(e - timedelta(days=2), names.GOOD_FRIDAY, "national"),
        Holiday(date(year, 4, 21), names.TIRADENTES, "national"),
        Holiday(date(year, 5, 1), names.LABOR_DAY, "national"),
        Holiday(e + timedelta(days=60), names.CORPUS_CHRISTI, "optional"),
        Holiday(date(year, 9, 7), names.INDEPENDENCE, "national"),
        Holiday(date(year, 10, 12), names.APARECIDA, "national"),
        Holiday(date(year, 11, 2), names.ALL_SOULS, "national"),
        Holiday(date(year, 11, 15), names.REPUBLIC, "national"),
        Holiday(date(year, 12, 25), names.CHRISTMAS, "national"),
    ]
    if year >= CONSCIENCIA_NEGRA_SINCE:
        items.append(Holiday(date(year, 11, 20), names.BLACK_CONSCIOUSNESS, "national"))
    return sorted(items, key=lambda h: h.date)


def holidays_between(start: date, end: date) -> list[Holiday]:
    result: list[Holiday] = []
    for year in range(start.year, end.year + 1):
        result.extend(h for h in holidays_of_year(year) if start <= h.date <= end)
    return result


def long_weekend(holiday: Holiday) -> str | None:
    """Descreve o efeito do feriado no fim de semana (segunda=0 ... domingo=6)."""
    names = T.HolidayNames
    if holiday.name == names.CARNIVAL_MONDAY:
        return T.LongWeekend.CARNIVAL
    if holiday.name in (names.CARNIVAL_TUESDAY, names.ASH_WEDNESDAY):
        return None  # já coberto pelo bloco do Carnaval
    weekday = holiday.date.weekday()
    if weekday in (0, 4):
        return T.LongWeekend.THREE_DAYS
    if weekday in (1, 3):
        return T.LongWeekend.BRIDGE
    if weekday in (5, 6):
        return T.LongWeekend.ON_WEEKEND
    return None
