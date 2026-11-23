"""Fase 3: sol, médias climáticas, feriados, câmbio (PTAX) e roteiros salvos — sem rede."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

from meu_passeio.db.session import Database
from meu_passeio.mcp_server.budget import currency as currency_module
from meu_passeio.mcp_server.budget import tools as budget_tools
from meu_passeio.mcp_server.budget.currency import PtaxClient
from meu_passeio.mcp_server.planning.holidays import (
    easter,
    holidays_between,
    holidays_of_year,
    long_weekend,
)
from meu_passeio.mcp_server.planning.tools import get_holidays
from meu_passeio.mcp_server.trips import tools as trip_tools
from meu_passeio.mcp_server.weather.climate import summarize, year_windows
from meu_passeio.mcp_server.weather.sun import sun_day
from meu_passeio.shared.schemas import TripDay, TripPlan

# --------------------------------------------------------------------------------- sol


def _hm(value) -> str:
    return value.strftime("%H:%M")


def test_sun_times_match_reference_values():
    # Referência: Open-Meteo para Rio Branco em 23/11/2026 (nascer 04:59, pôr 17:36).
    rio_branco = sun_day(date(2026, 11, 23), -9.947, -67.795, ZoneInfo("America/Rio_Branco"))
    assert _hm(rio_branco.sunrise) in {"04:58", "04:59", "05:00"}
    assert _hm(rio_branco.sunset) in {"17:35", "17:36", "17:37"}

    curitiba_winter = sun_day(date(2026, 6, 21), -25.43, -49.27, ZoneInfo("America/Sao_Paulo"))
    curitiba_summer = sun_day(date(2026, 12, 21), -25.43, -49.27, ZoneInfo("America/Sao_Paulo"))
    assert curitiba_summer.day_length_minutes > curitiba_winter.day_length_minutes + 150
    assert curitiba_winter.civil_dawn < curitiba_winter.sunrise
    assert curitiba_winter.golden_hour_evening_start < curitiba_winter.sunset


def test_sun_times_respect_daylight_saving_and_polar_night():
    lisbon = sun_day(date(2026, 7, 15), 38.72, -9.14, ZoneInfo("Europe/Lisbon"))
    assert lisbon.sunrise.utcoffset() == timedelta(hours=1)  # horário de verão
    assert _hm(lisbon.sunset).startswith("20:5") or _hm(lisbon.sunset).startswith("21:0")

    polar = sun_day(date(2026, 12, 21), 80.0, 15.0, ZoneInfo("Arctic/Longyearbyen"))
    assert polar.sunrise is None and polar.sunset is None and polar.day_length_minutes is None


# ---------------------------------------------------------------------------- clima


def test_year_windows_skip_recent_years_and_handle_leap_day():
    today = date(2026, 11, 23)
    windows = year_windows(date(2027, 2, 28), date(2027, 3, 1), 3, today)
    assert windows == [
        (date(2023, 2, 28), date(2023, 3, 1)),
        (date(2024, 2, 28), date(2024, 2, 29)),
        (date(2025, 2, 28), date(2025, 3, 1)),
    ]
    leap = year_windows(date(2028, 2, 29), date(2028, 2, 29), 2, today)
    # 2024 é bissexto (mantém 29/02); 2025 não (usa 28/02)
    assert leap == [
        (date(2024, 2, 29), date(2024, 2, 29)),
        (date(2025, 2, 28), date(2025, 2, 28)),
    ]


def test_climate_summary_uses_only_window_days():
    daily = {
        "time": ["2024-07-10", "2024-07-11", "2024-07-20", "2025-07-10", "2025-07-11"],
        "temperature_2m_max": [18.0, 16.0, 30.0, 20.0, 14.0],
        "temperature_2m_min": [8.0, 6.0, 20.0, 9.0, 3.0],
        "precipitation_sum": [0.0, 2.5, 50.0, 0.4, 1.0],
        "sunshine_duration": [36000, 18000, 0, 32400, 28800],
        "wind_speed_10m_max": [10, 12, 40, 8, 10],
    }
    windows = [(date(2024, 7, 10), date(2024, 7, 11)), (date(2025, 7, 10), date(2025, 7, 11))]
    stats = summarize(daily, windows)
    assert stats["days_sampled"] == 4  # 20/07 fica de fora
    assert stats["avg_temperature_max_c"] == 17.0
    assert (stats["highest_temperature_c"], stats["lowest_temperature_c"]) == (20.0, 3.0)
    assert stats["rainy_day_probability_pct"] == 50.0  # 2,5 mm e 1,0 mm
    assert stats["avg_sunshine_hours"] == 8.0  # (36000+18000+32400+28800)/4 s


# ---------------------------------------------------------------------------- feriados


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (2024, date(2024, 3, 31)),
        (2025, date(2025, 4, 20)),
        (2026, date(2026, 4, 5)),
        (2027, date(2027, 3, 28)),
    ],
)
def test_easter(year: int, expected: date):
    assert easter(year) == expected


def test_holidays_include_movable_dates_and_consciencia_negra_since_2024():
    names_2027 = {h.date: h.name for h in holidays_of_year(2027)}
    assert names_2027[date(2027, 3, 26)] == "Sexta-feira Santa"
    assert names_2027[date(2027, 2, 8)].startswith("Carnaval")
    assert names_2027[date(2027, 5, 27)] == "Corpus Christi"
    assert date(2027, 11, 20) in names_2027
    assert date(2023, 11, 20) not in {h.date for h in holidays_of_year(2023)}

    across_years = holidays_between(date(2026, 12, 20), date(2027, 1, 5))
    assert [h.date for h in across_years] == [date(2026, 12, 25), date(2027, 1, 1)]


def test_long_weekend_labels():
    by_date = {h.date: h for h in holidays_of_year(2027)}
    assert "3 dias" in long_weekend(by_date[date(2027, 1, 1)])  # sexta
    assert "emenda" in long_weekend(by_date[date(2027, 9, 7)])  # terça
    assert "fim de semana" in long_weekend(by_date[date(2027, 12, 25)])  # sábado
    assert "sábado a terça" in long_weekend(by_date[date(2027, 2, 8)])
    assert long_weekend(by_date[date(2027, 2, 9)]) is None  # terça de Carnaval já coberta


async def test_get_holidays_tool_defaults_to_end_of_year():
    result = await get_holidays(start_date=date(2027, 11, 1))
    assert [h.date for h in result.holidays] == [
        date(2027, 11, 2),
        date(2027, 11, 15),
        date(2027, 11, 20),
        date(2027, 12, 25),
    ]
    assert result.holidays[0].weekday == "terça" and result.notes


# ------------------------------------------------------------------------------ câmbio


def _ptax_transport(requests: list[httpx.Request]) -> httpx.MockTransport:
    rates = {"USD": 5.8889, "EUR": 6.4672}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        url = str(request.url)
        if "/Moedas?" in url:
            return httpx.Response(200, json={"value": [{"simbolo": "USD"}, {"simbolo": "EUR"}]})
        code = "USD" if "'USD'" in url else "EUR"
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "cotacaoCompra": 1,
                        "cotacaoVenda": 1,
                        "dataHoraCotacao": "2026-11-18 13:00:00.1",
                    },
                    {
                        "cotacaoCompra": rates[code] - 0.001,
                        "cotacaoVenda": rates[code],
                        "dataHoraCotacao": "2026-11-19 13:04:18.325373",
                        "tipoBoletim": "Fechamento",
                    },
                ]
            },
        )

    return httpx.MockTransport(handler)


async def test_currency_conversion_uses_latest_closing_and_literal_odata_url(monkeypatch):
    requests: list[httpx.Request] = []
    client = PtaxClient(httpx.AsyncClient(transport=_ptax_transport(requests)))
    monkeypatch.setattr(currency_module, "_ptax", client)

    usd = await budget_tools.convert_currency(amount=100, from_currency="usd")
    assert (usd.converted, usd.rate, usd.quote_date) == (588.89, 5.8889, date(2026, 11, 19))

    cross = await budget_tools.convert_currency(amount=50, from_currency="EUR", to_currency="USD")
    assert cross.converted == round(50 * 6.4672 / 5.8889, 2)
    assert cross.quotes == {"EUR": 6.4672, "USD": 5.8889}

    quote_url = str(next(r.url for r in requests if "CotacaoMoedaPeriodo" in str(r.url)))
    assert "@moeda='" in quote_url and "$filter=tipoBoletim%20eq%20'Fechamento'" in quote_url
    assert "%40" not in quote_url and "+" not in quote_url.split("?", 1)[1]

    with pytest.raises(Exception, match="XYZ"):
        await budget_tools.convert_currency(amount=1, from_currency="XYZ")
    with pytest.raises(Exception, match="iguais"):
        await budget_tools.convert_currency(amount=1, from_currency="BRL", to_currency="brl")


# ------------------------------------------------------------------------------ roteiros


async def test_trip_tools_save_list_get_update(tmp_path: Path, monkeypatch):
    db = Database(f"sqlite+aiosqlite:///{(tmp_path / 'trips.db').as_posix()}")
    await db.create_all()
    monkeypatch.setattr(trip_tools, "_db", db)

    plan = TripPlan(title="Fim de semana em Curitiba", itinerary=[TripDay(day_number=1)])
    saved = await trip_tools.save_trip(plan=plan)
    assert saved.id.startswith("trip_") and saved.id in saved.message

    listed = await trip_tools.list_trips()
    assert listed.count == 1 and listed.trips[0].title == "Fim de semana em Curitiba"

    updated = await trip_tools.update_trip(
        trip_id=saved.id, plan=plan.model_copy(update={"title": "Curitiba revisado"})
    )
    assert updated.title == "Curitiba revisado"
    trip = await trip_tools.get_trip(trip_id=saved.id)
    assert json.loads(trip.model_dump_json())["plan"]["title"] == "Curitiba revisado"

    with pytest.raises(Exception, match="não encontrado"):
        await trip_tools.get_trip(trip_id="trip_inexistente")
    await db.dispose()
