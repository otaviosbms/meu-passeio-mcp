"""Integração com Google Maps (Places API (New) e Routes API) usando respostas simuladas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from google_fakes import CENTER, FAKE_KEY, FakeGoogle, _place

from meu_passeio.mcp_server.common.http import ProviderError
from meu_passeio.mcp_server.maps import service as maps_service
from meu_passeio.mcp_server.maps.google import BRASILIA
from meu_passeio.mcp_server.places import service as places_service
from meu_passeio.mcp_server.places.opening_hours import opening_status
from meu_passeio.mcp_server.places.schemas import Place
from meu_passeio.shared.schemas import Coordinates, Waypoint


class FakeOsm:
    async def geocode(self, location: str):
        return CENTER, "Curitiba, Paraná, Brasil"

    async def search_by_categories(self, **kwargs: Any):
        return [Place(id="osm:node:1", name="Parque OSM")], 1


# ----------------------------------------------------------------------------- places


async def test_search_uses_filters_field_mask_and_ranks_by_quality(fake_google: FakeGoogle):
    fake_google.responses["places:searchText"] = {
        "places": [
            _place("a", "Parque Pequeno", 5.0, 3),
            _place("b", "Parque Barigui", 4.7, 3000, priceLevel="PRICE_LEVEL_FREE"),
            _place("c", "Parque Fechado", 4.9, 900, businessStatus="CLOSED_PERMANENTLY"),
        ]
    }
    result = await places_service.search(
        categories=["park"],
        query=None,
        location="Curitiba",
        coordinates=CENTER,
        radius_km=10,
        limit=10,
        min_rating=4.5,
        open_now=True,
    )

    request = fake_google.requests[0]
    assert request.headers["X-Goog-Api-Key"] == FAKE_KEY
    assert "places.rating" in request.headers["X-Goog-FieldMask"]
    assert "places.priceRange" in request.headers["X-Goog-FieldMask"]
    body = fake_google.bodies("places:searchText")[0]
    assert body["includedType"] == "park"
    assert body["minRating"] == 4.5 and body["openNow"] is True
    assert body["languageCode"] == "pt-BR"
    assert body["locationBias"]["circle"]["radius"] == 10_000
    assert "parque" in body["textQuery"] and "Curitiba" in body["textQuery"]

    assert result.source == "google_maps" and result.attribution
    assert [p.name for p in result.places] == ["Parque Barigui", "Parque Pequeno"]
    assert result.places[0].price_level == "free"
    assert result.places[0].user_rating_count == 3000


async def test_restaurant_price_range_is_parsed(fake_google: FakeGoogle):
    fake_google.responses["places:searchText"] = {
        "places": [
            _place(
                "r1",
                "Cantina",
                4.6,
                1200,
                priceRange={
                    "startPrice": {"currencyCode": "BRL", "units": "60"},
                    "endPrice": {"currencyCode": "BRL", "units": "80", "nanos": 500000000},
                },
            )
        ]
    }
    result = await places_service.search(
        categories=["restaurant"],
        query=None,
        location=None,
        coordinates=CENTER,
        radius_km=5,
        limit=5,
        cuisine="italiana",
        price_levels=["moderate"],
    )
    body = fake_google.bodies("places:searchText")[0]
    assert body["priceLevels"] == ["PRICE_LEVEL_MODERATE"]
    assert body["textQuery"].startswith("italiana restaurante")
    price = result.places[0].price_range
    assert price is not None and (price.min, price.max, price.currency) == (60, 80.5, "BRL")


async def test_google_error_falls_back_to_osm_without_leaking_key(
    fake_google: FakeGoogle, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(places_service, "_osm", FakeOsm())
    fake_google.responses["places:searchText"] = {
        "error": {"status": "PERMISSION_DENIED", "message": "Places API (New) is not enabled"}
    }
    fake_google.status["places:searchText"] = 403
    result = await places_service.search(
        categories=["park"], query=None, location=None, coordinates=CENTER, radius_km=5, limit=5
    )
    assert result.source == "openstreetmap"
    assert result.places[0].name == "Parque OSM"
    assert any("PERMISSION_DENIED" in n and "not enabled" in n for n in result.notes)
    assert all(FAKE_KEY not in n for n in result.notes)


async def test_without_key_uses_osm(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(places_service, "google", lambda: None)
    monkeypatch.setattr(places_service, "_osm", FakeOsm())
    result = await places_service.search(
        categories=["park"], query=None, location="Curitiba", coordinates=None, radius_km=5, limit=5
    )
    assert result.source == "openstreetmap"
    assert any("GOOGLE_MAPS_API_KEY" in n for n in result.notes)


async def test_details_parses_hours_reviews_and_amenities(fake_google: FakeGoogle):
    fake_google.responses["/places/abc"] = _place(
        "abc",
        "Museu Oscar Niemeyer",
        4.8,
        50000,
        editorialSummary={"text": "Museu de arte em edifício icônico."},
        regularOpeningHours={
            "weekdayDescriptions": ["segunda-feira: Fechado", "terça-feira: 10:00–18:00"]
        },
        reviews=[
            {
                "rating": 5,
                "text": {"text": "x" * 2000, "languageCode": "pt"},
                "relativePublishTimeDescription": "há 2 semanas",
                "authorAttribution": {"displayName": "Ana"},
            }
        ],
        parkingOptions={"paidParkingLot": True},
        accessibilityOptions={"wheelchairAccessibleEntrance": True},
        goodForChildren=True,
    )
    info = await places_service.details("abc")
    assert info.description == "Museu de arte em edifício icônico."
    assert info.opening_hours_weekdays[0] == "segunda-feira: Fechado"
    assert info.reviews[0].author == "Ana" and len(info.reviews[0].text or "") == 600
    assert info.amenities == {
        "goodForChildren": True,
        "paidParkingLot": True,
        "wheelchairAccessibleEntrance": True,
    }
    assert "reviews" in fake_google.requests[0].headers["X-Goog-FieldMask"]


async def test_check_opening_uses_current_hours_in_next_week(fake_google: FakeGoogle):
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=11, minute=0)
    google_day = (tomorrow.weekday() + 1) % 7
    fake_google.responses["/places/xyz"] = {
        "id": "xyz",
        "displayName": {"text": "Café"},
        "currentOpeningHours": {
            "periods": [
                {
                    "open": {"day": google_day, "hour": 9, "minute": 0},
                    "close": {"day": google_day, "hour": 12, "minute": 0},
                }
            ]
        },
        "regularOpeningHours": {"weekdayDescriptions": ["…"]},
    }
    check = await places_service.check_opening("xyz", tomorrow)
    assert check.is_open is True and check.closes_at and check.closes_at.endswith("12:00")
    assert check.notes == []


# ---------------------------------------------------------------------- opening hours


def _period(open_day: int, open_h: int, close_day: int, close_h: int) -> dict[str, Any]:
    return {
        "open": {"day": open_day, "hour": open_h, "minute": 0},
        "close": {"day": close_day, "hour": close_h, "minute": 0},
    }


def test_opening_status_regular_overnight_and_24h():
    weekdays = [_period(d, 9, d, 18) for d in range(1, 6)]  # seg–sex 9h–18h
    monday_10 = datetime(2026, 11, 23, 10, 0)  # segunda-feira
    sunday_10 = datetime(2026, 11, 22, 10, 0)

    open_status = opening_status(weekdays, monday_10)
    assert open_status.is_open is True and open_status.closes_at == "segunda 18:00"

    closed = opening_status(weekdays, sunday_10)
    assert closed.is_open is False and closed.opens_at == "segunda 09:00"

    bar = [_period(5, 20, 6, 2)]  # sexta 20h – sábado 2h
    assert opening_status(bar, datetime(2026, 11, 28, 1, 0)).is_open is True  # sábado 1h

    saturday_bar = [_period(6, 22, 0, 3)]  # sábado 22h – domingo 3h (vira a semana)
    assert opening_status(saturday_bar, datetime(2026, 11, 29, 2, 0)).is_open is True

    always = [{"open": {"day": 0, "hour": 0, "minute": 0}}]
    assert opening_status(always, sunday_10).is_open is True
    assert opening_status([], sunday_10).is_open is None


# ----------------------------------------------------------------------------- routes

ROUTE = {
    "distanceMeters": 180_000,
    "duration": "8100s",
    "staticDuration": "7200s",
    "description": "BR-277",
    "travelAdvisory": {
        "tollInfo": {"estimatedPrice": [{"currencyCode": "BRL", "units": "24", "nanos": 300000000}]}
    },
    "legs": [{"distanceMeters": 180_000, "duration": "8100s"}],
}


async def test_route_with_traffic_and_tolls(fake_google: FakeGoogle):
    fake_google.responses["directions/v2:computeRoutes"] = {"routes": [ROUTE]}
    departure = datetime.now() + timedelta(days=2)
    result = await maps_service.route(
        Waypoint(address="Curitiba, PR"),
        Waypoint(coordinates=Coordinates(latitude=-25.52, longitude=-48.51)),
        mode="driving",
        departure_time=departure,
        alternatives=True,
        avoid_tolls=False,
        avoid_highways=False,
        include_polyline=False,
    )
    body = fake_google.bodies("computeRoutes")[0]
    assert body["routingPreference"] == "TRAFFIC_AWARE"
    assert body["extraComputations"] == ["TOLLS"]
    assert body["computeAlternativeRoutes"] is True
    assert body["origin"] == {"address": "Curitiba, PR"}
    expected = departure.replace(tzinfo=BRASILIA).astimezone(UTC)
    assert body["departureTime"] == expected.strftime("%Y-%m-%dT%H:%M:%SZ")

    route = result.routes[0]
    assert result.source == "google_maps" and route.traffic_aware
    assert (route.duration_seconds, route.static_duration_seconds) == (8100, 7200)
    assert route.tolls.has_tolls and route.tolls.estimated_price == 24.3
    assert route.tolls.currency == "BRL"


async def test_departure_in_past_is_rejected(fake_google: FakeGoogle):
    with pytest.raises(ProviderError, match="futuro"):
        await maps_service.tolls(
            Waypoint(address="A"),
            Waypoint(address="B"),
            round_trip=False,
            departure_time=datetime.now() - timedelta(hours=1),
        )


async def test_toll_round_trip_total(fake_google: FakeGoogle):
    fake_google.responses["directions/v2:computeRoutes"] = {"routes": [ROUTE]}
    estimate = await maps_service.tolls(
        Waypoint(address="Curitiba"),
        Waypoint(address="Guaratuba"),
        round_trip=True,
        departure_time=None,
    )
    assert estimate.has_tolls and estimate.total_estimated == 48.6
    assert estimate.currency == "BRL" and estimate.inbound is not None
    assert len(fake_google.bodies("computeRoutes")) == 2


async def test_toll_unknown_price_and_no_tolls(fake_google: FakeGoogle):
    fake_google.responses["directions/v2:computeRoutes"] = {
        "routes": [{**ROUTE, "travelAdvisory": {"tollInfo": {}}}]
    }
    unknown = await maps_service.tolls(
        Waypoint(address="A"), Waypoint(address="B"), round_trip=False, departure_time=None
    )
    assert unknown.has_tolls is True and unknown.total_estimated is None

    fake_google.responses["directions/v2:computeRoutes"] = {
        "routes": [{k: v for k, v in ROUTE.items() if k != "travelAdvisory"}]
    }
    free = await maps_service.tolls(
        Waypoint(address="A"), Waypoint(address="B"), round_trip=False, departure_time=None
    )
    assert free.has_tolls is False and free.total_estimated == 0.0


async def test_optimize_maps_google_order_back_to_stop_indices(fake_google: FakeGoogle):
    fake_google.responses["directions/v2:computeRoutes"] = {
        "routes": [{**ROUTE, "optimizedIntermediateWaypointIndex": [2, 0, 1]}]
    }
    stops = [Waypoint(address=f"P{i}") for i in range(5)]
    result = await maps_service.optimize(
        stops, mode="driving", roundtrip=False, departure_time=None
    )
    body = fake_google.bodies("computeRoutes")[0]
    assert body["optimizeWaypointOrder"] is True and len(body["intermediates"]) == 3
    assert result.order == [0, 3, 1, 2, 4]


async def test_matrix_fills_cells_and_skips_missing_routes(fake_google: FakeGoogle):
    fake_google.responses["distanceMatrix/v2:computeRouteMatrix"] = [
        {
            "originIndex": 0,
            "destinationIndex": 0,
            "condition": "ROUTE_EXISTS",
            "distanceMeters": 1000,
            "duration": "300s",
            "staticDuration": "240s",
        },
        {"originIndex": 0, "destinationIndex": 1, "condition": "ROUTE_NOT_FOUND"},
    ]
    result = await maps_service.matrix(
        [Waypoint(address="A")],
        [Waypoint(address="B"), Waypoint(address="C")],
        mode="driving",
        departure_time=None,
    )
    assert result.durations_seconds == [[300, None]]
    assert result.static_durations_seconds == [[240, None]]
    assert result.traffic_aware is True
