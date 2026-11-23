"""Horários do sol calculados localmente (algoritmo da NOAA, precisão de ~1 minuto).

Funciona para qualquer data, sem API. Os horários são calculados em UTC e convertidos para o
fuso do lugar (``zoneinfo``), o que já considera horário de verão onde houver.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

SUNRISE_ELEVATION = -0.833  # refração atmosférica + raio aparente do sol
CIVIL_TWILIGHT_ELEVATION = -6.0
GOLDEN_HOUR_ELEVATION = 6.0


def _julian_day(day: date) -> float:
    return day.toordinal() + 1721424.5  # 0h UT do dia


def _solar_parameters(jd: float) -> tuple[float, float]:
    """Declinação (radianos) e equação do tempo (minutos) para o dia juliano."""
    t = (jd - 2451545.0) / 36525.0
    l0 = math.radians((280.46646 + t * (36000.76983 + t * 0.0003032)) % 360)
    m = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (
        math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2 * m) * (0.019993 - 0.000101 * t)
        + math.sin(3 * m) * 0.000289
    )
    omega = math.radians(125.04 - 1934.136 * t)
    apparent_longitude = math.radians(math.degrees(l0) + c - 0.00569 - 0.00478 * math.sin(omega))
    eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    declination = math.asin(math.sin(eps) * math.sin(apparent_longitude))
    y = math.tan(eps / 2) ** 2
    equation_of_time = 4 * math.degrees(
        y * math.sin(2 * l0)
        - 2 * e * math.sin(m)
        + 4 * e * y * math.sin(m) * math.cos(2 * l0)
        - 0.5 * y * y * math.sin(4 * l0)
        - 1.25 * e * e * math.sin(2 * m)
    )
    return declination, equation_of_time


def _event_minutes_utc(
    day: date, latitude: float, longitude: float, elevation: float, rising: bool
) -> float | None:
    """Minutos após 0h UTC em que o sol cruza a elevação dada; None se não cruza no dia."""
    lat = math.radians(latitude)
    minutes = 720.0 - 4 * longitude  # chute inicial: meio-dia solar
    for _ in range(3):  # refina recalculando os parâmetros no horário do evento
        declination, eqtime = _solar_parameters(_julian_day(day) + minutes / 1440)
        cos_h = (math.sin(math.radians(elevation)) - math.sin(lat) * math.sin(declination)) / (
            math.cos(lat) * math.cos(declination)
        )
        if cos_h > 1 or cos_h < -1:
            return None  # sol sempre abaixo/acima dessa elevação (regiões polares)
        hour_angle = math.degrees(math.acos(cos_h))
        noon = 720.0 - 4 * longitude - eqtime
        minutes = noon - 4 * hour_angle if rising else noon + 4 * hour_angle
    return minutes


def solar_noon_minutes_utc(day: date, longitude: float) -> float:
    _, eqtime = _solar_parameters(_julian_day(day) + (720 - 4 * longitude) / 1440)
    return 720.0 - 4 * longitude - eqtime


@dataclass
class SunDay:
    date: date
    sunrise: datetime | None
    sunset: datetime | None
    solar_noon: datetime
    civil_dawn: datetime | None
    civil_dusk: datetime | None
    golden_hour_morning_end: datetime | None
    golden_hour_evening_start: datetime | None

    @property
    def day_length_minutes(self) -> int | None:
        if self.sunrise and self.sunset:
            return round((self.sunset - self.sunrise).total_seconds() / 60)
        return None


def sun_day(day: date, latitude: float, longitude: float, tz: ZoneInfo) -> SunDay:
    base = datetime(day.year, day.month, day.day, tzinfo=UTC)

    def at(minutes: float | None) -> datetime | None:
        if minutes is None:
            return None
        return (base + timedelta(minutes=minutes)).astimezone(tz).replace(second=0, microsecond=0)

    def event(elevation: float, rising: bool) -> datetime | None:
        return at(_event_minutes_utc(day, latitude, longitude, elevation, rising))

    return SunDay(
        date=day,
        sunrise=event(SUNRISE_ELEVATION, True),
        sunset=event(SUNRISE_ELEVATION, False),
        solar_noon=at(solar_noon_minutes_utc(day, longitude)),  # type: ignore[arg-type]
        civil_dawn=event(CIVIL_TWILIGHT_ELEVATION, True),
        civil_dusk=event(CIVIL_TWILIGHT_ELEVATION, False),
        golden_hour_morning_end=event(GOLDEN_HOUR_ELEVATION, True),
        golden_hour_evening_start=event(GOLDEN_HOUR_ELEVATION, False),
    )
