"""Fase 2: preços da ANP, custo de refeição, bate-volta e agenda do dia (sem rede)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from google_fakes import CENTER, FakeGoogle, _place

from meu_passeio.mcp_server.budget import fuel as fuel_module
from meu_passeio.mcp_server.budget import meals
from meu_passeio.mcp_server.budget import tools as budget_tools
from meu_passeio.mcp_server.budget.fuel import AnpFuelPrices, Dataset, normalize, parse_csv
from meu_passeio.mcp_server.planning import service as planning
from meu_passeio.mcp_server.planning.schemas import DayStop
from meu_passeio.shared.schemas import Coordinates, Waypoint

HEADER = (
    "﻿Regiao - Sigla;Estado - Sigla;Municipio;Revenda;CNPJ da Revenda;Nome da Rua;"
    "Numero Rua;Complemento;Bairro;Cep;Produto;Data da Coleta;Valor de Venda;Valor de Compra;"
    "Unidade de Medida;Bandeira\n"
)


def _row(uf: str, city: str, product: str, day: str, price: str, unit: str = "R$ / litro") -> str:
    return (
        f"SE;{uf};{city};POSTO;00;RUA;1;;BAIRRO;00000-000;{product};{day};{price};;{unit};BRANCA\n"
    )


ANP_CSV = HEADER + "".join(
    [
        _row("SP", "MARILIA", "GASOLINA", "10/11/2026", "6,19"),
        _row("SP", "MARILIA", "GASOLINA", "12/11/2026", "6,39"),
        _row("SP", "MARILIA", "GASOLINA", "13/11/2026", "6,29"),
        _row(
            "SP", "MARILIA", "GASOLINA", "20/10/2026", "9,99"
        ),  # antiga: fora da janela de 14 dias
        _row("SP", "BAURU", "GASOLINA", "12/11/2026", "6,09"),
        _row("SP", "SAO PAULO", "GNV", "12/11/2026", "5,25", "R$ / m³"),
        _row("PR", "CURITIBA", "ETANOL", "12/11/2026", "4,69"),
    ]
)


class FakeAnp(AnpFuelPrices):
    def __init__(self) -> None:
        super().__init__(client=None)  # type: ignore[arg-type]

    async def _download(self, name: str) -> Dataset:
        dataset = Dataset(loaded_at=1e18)
        parse_csv(ANP_CSV, dataset)
        return dataset


# --------------------------------------------------------------------------------- ANP


def test_normalize_matches_anp_city_names():
    assert normalize("Marília") == "MARILIA"
    assert normalize(" são paulo ") == "SAO PAULO"


async def test_anp_lookup_levels_and_recent_window():
    anp = FakeAnp()
    stats, level, city = await anp.lookup("gasolina", "sp", "Marília")
    assert (level, city) == ("municipality", "MARILIA")
    assert stats.stations == 3  # a coleta de 20/10 ficou fora da janela de 14 dias
    assert stats.average == pytest.approx(6.29) and (stats.minimum, stats.maximum) == (6.19, 6.39)
    assert stats.period_end == date(2026, 11, 13)

    stats, level, _ = await anp.lookup("gasolina", "SP", "Garça")
    assert level == "state" and stats.stations == 4

    stats, level, _ = await anp.lookup("etanol", "SC", None)
    assert level == "national" and stats.average == 4.69

    gnv, _, _ = await anp.lookup("gnv", "SP", "São Paulo")
    assert gnv.unit == "R$/m³"


async def test_fuel_cost_uses_anp_price(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(fuel_module, "_anp", FakeAnp())
    result = await budget_tools.calculate_fuel_cost(
        distance_km=120, state="SP", city="Marília", vehicle_consumption_km_per_liter=10
    )
    assert result.price_source == "anp"
    assert result.parameters["fuel_price_per_liter"] == pytest.approx(6.29)
    assert result.estimated_cost == pytest.approx(240 / 10 * 6.29, abs=0.01)
    assert "R$ 6,29" in result.notes[0]

    with pytest.raises(Exception, match="fuel_price_per_liter ou state"):
        await budget_tools.calculate_fuel_cost(distance_km=10)


# ------------------------------------------------------------------------------- meals


def _priced(pid: str, low: int, high: int, **extra: Any) -> dict[str, Any]:
    return _place(
        pid,
        f"Restaurante {pid}",
        4.5,
        500,
        priceRange={
            "startPrice": {"currencyCode": "BRL", "units": str(low)},
            "endPrice": {"currencyCode": "BRL", "units": str(high)},
        },
        **extra,
    )


async def test_meal_cost_median_and_quartiles(fake_google: FakeGoogle):
    fake_google.responses["places:searchText"] = {
        "places": [
            _priced("a", 40, 60),  # 50
            _priced("b", 60, 80),  # 70
            _priced("c", 80, 100),  # 90
            _priced("d", 100, 140),  # 120
            _place("e", "Sem preço", 4.6, 300, priceLevel="PRICE_LEVEL_MODERATE"),
        ]
    }
    estimate = await meals.estimate_meal_cost(
        meal="dinner",
        location=None,
        coordinates=CENTER,
        cuisine="italiana",
        radius_km=5,
        min_rating=4.0,
    )
    body = fake_google.bodies("places:searchText")[0]
    assert body["includedType"] == "restaurant" and "jantar" in body["textQuery"]
    assert estimate.per_person_median == 80
    assert (estimate.typical_min, estimate.typical_max) == (65, 97.5)
    assert estimate.sample_size == 4 and estimate.places_considered == 5
    assert estimate.price_level_counts == {"moderate": 1}
    assert estimate.currency == "BRL"


async def test_meal_cost_refuses_to_guess_with_few_prices(fake_google: FakeGoogle):
    fake_google.responses["places:searchText"] = {"places": [_priced("a", 40, 60)]}
    estimate = await meals.estimate_meal_cost(
        meal="lunch", location=None, coordinates=CENTER, cuisine=None, radius_km=5, min_rating=4
    )
    assert estimate.per_person_median is None and estimate.notes


# --------------------------------------------------------------------------- day trips


def _town_place(pid: str, town: str, lat: float, rating: float, count: int) -> dict[str, Any]:
    return _place(
        pid,
        f"Atração {pid}",
        rating,
        count,
        location={"latitude": lat, "longitude": -49.94},
        addressComponents=[
            {"longText": town, "types": ["administrative_area_level_2", "political"]},
            {"shortText": "SP", "types": ["administrative_area_level_1"]},
        ],
    )


async def test_suggest_day_trips_groups_by_town_and_filters_by_drive_time(
    fake_google: FakeGoogle,
):
    origin = Coordinates(latitude=-22.21, longitude=-49.94)  # Marília
    fake_google.responses["places:searchText"] = {
        "places": [
            _town_place("m1", "Marília", -22.22, 4.9, 5000),  # a 1 km: excluída (cidade de origem)
            _town_place("g1", "Garça", -22.21 - 0.3, 4.7, 2000),
            _town_place("g2", "Garça", -22.21 - 0.31, 4.5, 800),
            _town_place("b1", "Bauru", -22.21 - 0.9, 4.8, 9000),
            _town_place("x1", "Longe", -22.21 - 1.5, 4.9, 9000),
        ]
    }
    fake_google.responses["distanceMatrix/v2:computeRouteMatrix"] = [
        # ordem da matriz = ordem do score: Garça (2 atrações), Bauru, Longe
        {
            "originIndex": 0,
            "destinationIndex": 0,
            "condition": "ROUTE_EXISTS",
            "duration": "2700s",
            "distanceMeters": 40000,
        },
        {
            "originIndex": 0,
            "destinationIndex": 1,
            "condition": "ROUTE_EXISTS",
            "duration": "6600s",
            "staticDuration": "6000s",
            "distanceMeters": 110000,
        },
        {
            "originIndex": 0,
            "destinationIndex": 2,
            "condition": "ROUTE_EXISTS",
            "duration": "9000s",
            "distanceMeters": 170000,
        },
    ]
    result = await planning.suggest_day_trips(
        origin=None,
        origin_coordinates=origin,
        max_drive_hours=2,
        interests=["tourist_attraction"],
        min_rating=4.3,
        min_reviews=100,
        min_distance_km=20,
        departure_time=None,
        limit=5,
    )
    search = fake_google.bodies("places:searchText")[0]
    assert "rectangle" in search["locationRestriction"]
    assert "addressComponents" in fake_google.requests[0].headers["X-Goog-FieldMask"]
    # Garça soma 2 atrações e fica à frente de Bauru; "Longe" passa de 2h; Marília é a origem.
    assert [d.town for d in result.destinations] == ["Garça", "Bauru"]
    garca, bauru = result.destinations
    assert garca.attraction_count == 2 and garca.drive_minutes == 45
    assert (bauru.drive_minutes, bauru.drive_minutes_no_traffic, bauru.distance_km) == (
        110,
        100,
        110,
    )


# ---------------------------------------------------------------------------- day plan


def _hours(day: date, open_h: int, close_h: int) -> dict[str, Any]:
    google_day = (day.weekday() + 1) % 7
    return {
        "displayName": {"text": "Lugar"},
        "regularOpeningHours": {
            "periods": [
                {
                    "open": {"day": google_day, "hour": open_h, "minute": 0},
                    "close": {"day": google_day, "hour": close_h, "minute": 0},
                }
            ]
        },
    }


async def test_plan_day_orders_schedules_and_checks_hours(fake_google: FakeGoogle):
    day = date.today() + timedelta(days=30)  # além de 7 dias: usa horário regular
    fake_google.responses["directions/v2:computeRoutes"] = {
        "routes": [
            {
                "distanceMeters": 30000,
                "duration": "3600s",
                "optimizedIntermediateWaypointIndex": [1, 0, 2],
                "legs": [
                    {"distanceMeters": 10000, "duration": "1200s"},  # partida -> B
                    {"distanceMeters": 5000, "duration": "600s"},  # B -> A
                    {"distanceMeters": 5000, "duration": "600s"},  # A -> C
                    {"distanceMeters": 10000, "duration": "1200s"},  # C -> volta
                ],
            }
        ]
    }
    fake_google.responses["/places/A"] = _hours(day, 9, 18)
    fake_google.responses["/places/B"] = _hours(day, 10, 17)  # chega 09:20: espera até 10:00
    fake_google.responses["/places/C"] = _hours(day, 8, 12)  # visita termina depois das 12:00

    itinerary = await planning.plan_day(
        start=Waypoint(address="Hotel"),
        stops=[
            DayStop(place=Waypoint(place_id="A"), name="Museu A", visit_minutes=60),
            DayStop(place=Waypoint(place_id="B"), name="Parque B", visit_minutes=90),
            DayStop(place=Waypoint(place_id="C"), name="Mercado C", visit_minutes=60),
        ],
        day=day,
        start_time="09:00",
        end=None,
        mode="driving",
        keep_order=False,
    )
    body = fake_google.bodies("computeRoutes")[0]
    assert body["optimizeWaypointOrder"] is True and "departureTime" in body

    names = [s.name for s in itinerary.stops]
    assert names == ["Parque B", "Museu A", "Mercado C"]
    b, a, c = itinerary.stops
    assert (b.arrival, b.wait_minutes, b.visit_start, b.departure) == (
        "09:20",
        40,
        "10:00",
        "11:30",
    )
    assert (a.arrival, a.departure, a.is_open_on_arrival) == ("11:40", "12:40", True)
    assert c.arrival == "12:50" and c.is_open_on_arrival is False
    assert any("fechado" in w for w in c.warnings)
    assert itinerary.end_arrival == "14:10"
    assert itinerary.total_travel_minutes == 60 and itinerary.total_distance_km == 30
    assert itinerary.traffic_aware is True and itinerary.order_optimized is True


async def test_plan_day_warns_when_place_closes_during_visit(fake_google: FakeGoogle):
    day = date.today() + timedelta(days=30)
    fake_google.responses["directions/v2:computeRoutes"] = {
        "routes": [
            {
                "distanceMeters": 2000,
                "duration": "600s",
                "legs": [
                    {"distanceMeters": 1000, "duration": "300s"},
                    {"distanceMeters": 1000, "duration": "300s"},
                ],
            }
        ]
    }
    fake_google.responses["/places/Z"] = _hours(day, 8, 10)
    itinerary = await planning.plan_day(
        start=Waypoint(address="Hotel"),
        stops=[DayStop(place=Waypoint(place_id="Z"), visit_minutes=120)],
        day=day,
        start_time="09:00",
        end=None,
        mode="driving",
        keep_order=True,
    )
    stop = itinerary.stops[0]
    assert stop.name == "Lugar"  # preenchido pelo Google
    assert stop.closes_at == "10:00" and any("fecha às 10:00" in w for w in stop.warnings)
    assert itinerary.order_optimized is False


async def test_plan_day_rejects_bad_start_time(fake_google: FakeGoogle):
    with pytest.raises(Exception, match="HH:MM"):
        await planning.plan_day(
            start=Waypoint(address="Hotel"),
            stops=[DayStop(place=Waypoint(address="X"))],
            day=date.today(),
            start_time="9h",
            end=None,
            mode="driving",
            keep_order=True,
        )
