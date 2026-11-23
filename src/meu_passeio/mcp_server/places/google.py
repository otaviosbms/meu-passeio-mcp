"""Provider de lugares baseado no Google Places API (New).

Docs: https://developers.google.com/maps/documentation/places/web-service/op-overview
Os dados vêm do Google e devem ser exibidos com atribuição ("Google Maps").
Campos não retornados pelo Google ficam ``None`` — nunca inventados.
"""

from __future__ import annotations

from typing import Any

from meu_passeio.mcp_server.common.geo import haversine_km
from meu_passeio.mcp_server.common.google import GoogleMapsClient, money_to_float
from meu_passeio.mcp_server.common.http import ProviderError
from meu_passeio.mcp_server.places.schemas import (
    Place,
    PlaceDetails,
    PriceLevel,
    PriceRange,
    Review,
)
from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import places as T

BASE_URL = "https://places.googleapis.com/v1"
MAX_PAGE_SIZE = 20
MAX_BIAS_RADIUS_M = 50_000
MAX_REVIEW_CHARS = 600

# Campos pedidos nas buscas (o Google cobra pelo nível do campo mais caro).
SEARCH_FIELDS = [
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "rating",
    "userRatingCount",
    "priceLevel",
    "priceRange",
    "primaryType",
    "primaryTypeDisplayName",
    "currentOpeningHours.openNow",
    "businessStatus",
    "googleMapsUri",
]
DETAIL_FIELDS = SEARCH_FIELDS + [
    "websiteUri",
    "nationalPhoneNumber",
    "editorialSummary",
    "regularOpeningHours",
    "utcOffsetMinutes",
    "reviews",
    "accessibilityOptions",
    "parkingOptions",
    "paymentOptions",
    "goodForChildren",
    "allowsDogs",
    "outdoorSeating",
    "reservable",
    "servesVegetarianFood",
]
HOURS_FIELDS = [
    "id",
    "displayName",
    "regularOpeningHours",
    "currentOpeningHours",
    "utcOffsetMinutes",
    "businessStatus",
]

# Categoria do Meu Passeio -> (tipo do Google, termo de busca em português)
CATEGORY_TO_GOOGLE: dict[str, tuple[str | None, str]] = {
    "park": ("park", "parque"),
    "nature_reserve": ("national_park", "reserva natural"),
    "viewpoint": (None, "mirante"),
    "waterfall": (None, "cachoeira"),
    "beach": (None, "praia"),
    "hiking_area": ("hiking_area", "trilha"),
    "tourist_attraction": ("tourist_attraction", "atrações turísticas"),
    "museum": ("museum", "museu"),
    "art_gallery": ("art_gallery", "galeria de arte"),
    "historic": (None, "ponto histórico"),
    "theatre": ("performing_arts_theater", "teatro"),
    "zoo": ("zoo", "zoológico"),
    "aquarium": ("aquarium", "aquário"),
    "theme_park": ("amusement_park", "parque de diversões"),
    "place_of_worship": ("church", "igreja"),
    "shopping_mall": ("shopping_mall", "shopping"),
    "restaurant": ("restaurant", "restaurante"),
    "cafe": ("cafe", "café"),
    "bar": ("bar", "bar"),
    "bakery": ("bakery", "padaria"),
    "fast_food": ("fast_food_restaurant", "lanchonete"),
    "ice_cream": ("ice_cream_shop", "sorveteria"),
}

_PRICE_TO_GOOGLE: dict[str, str] = {
    "free": "PRICE_LEVEL_FREE",
    "inexpensive": "PRICE_LEVEL_INEXPENSIVE",
    "moderate": "PRICE_LEVEL_MODERATE",
    "expensive": "PRICE_LEVEL_EXPENSIVE",
    "very_expensive": "PRICE_LEVEL_VERY_EXPENSIVE",
}
_GOOGLE_TO_PRICE: dict[str, PriceLevel] = {v: k for k, v in _PRICE_TO_GOOGLE.items()}  # type: ignore[misc]

_AMENITY_FIELDS = (
    "goodForChildren",
    "allowsDogs",
    "outdoorSeating",
    "reservable",
    "servesVegetarianFood",
)


def _mask(fields: list[str], prefix: str = "") -> str:
    return ",".join(f"{prefix}{f}" for f in fields)


def _circle(center: Coordinates, radius_m: float) -> dict[str, Any]:
    return {
        "circle": {
            "center": {"latitude": center.latitude, "longitude": center.longitude},
            "radius": min(radius_m, MAX_BIAS_RADIUS_M),
        }
    }


def _price_range(raw: dict[str, Any] | None) -> PriceRange | None:
    if not raw:
        return None
    start, end = raw.get("startPrice"), raw.get("endPrice")
    currency = (start or end or {}).get("currencyCode")
    return PriceRange(min=money_to_float(start), max=money_to_float(end), currency=currency)


def _to_place(raw: dict[str, Any], center: Coordinates | None) -> Place:
    location = raw.get("location") or {}
    coords = (
        Coordinates(latitude=location["latitude"], longitude=location["longitude"])
        if "latitude" in location and "longitude" in location
        else None
    )
    distance = (
        round(haversine_km(center.latitude, center.longitude, coords.latitude, coords.longitude), 2)
        if center and coords
        else None
    )
    current = raw.get("currentOpeningHours") or {}
    return Place(
        id=raw["id"],
        name=(raw.get("displayName") or {}).get("text") or raw["id"],
        category=raw.get("primaryType"),
        category_label=(raw.get("primaryTypeDisplayName") or {}).get("text"),
        address=raw.get("formattedAddress"),
        coordinates=coords,
        distance_km=distance,
        rating=raw.get("rating"),
        user_rating_count=raw.get("userRatingCount"),
        price_level=_GOOGLE_TO_PRICE.get(raw.get("priceLevel", "")),
        price_range=_price_range(raw.get("priceRange")),
        open_now=current.get("openNow"),
        business_status=raw.get("businessStatus"),
        google_maps_uri=raw.get("googleMapsUri"),
        source=T.Sources.GOOGLE,
    )


def _filter_places(
    places: list[Place],
    *,
    min_reviews: int | None,
    radius_km: float | None,
) -> list[Place]:
    result = []
    for place in places:
        if place.business_status and place.business_status != "OPERATIONAL":
            continue
        if min_reviews and (place.user_rating_count or 0) < min_reviews:
            continue
        if radius_km and place.distance_km is not None and place.distance_km > radius_km:
            continue
        result.append(place)
    return result


class GooglePlacesProvider:
    def __init__(self, client: GoogleMapsClient) -> None:
        self._client = client

    def _locale(self) -> dict[str, str]:
        return {"languageCode": self._client.language, "regionCode": self._client.region}

    async def text_search(
        self,
        *,
        text_query: str,
        center: Coordinates | None,
        radius_km: float | None,
        limit: int,
        included_type: str | None = None,
        min_rating: float | None = None,
        min_reviews: int | None = None,
        open_now: bool | None = None,
        price_levels: list[str] | None = None,
        rank_by_distance: bool = False,
        route_polyline: str | None = None,
    ) -> tuple[list[Place], int]:
        body: dict[str, Any] = {
            "textQuery": text_query,
            "pageSize": MAX_PAGE_SIZE,
            **self._locale(),
        }
        if center is not None and radius_km and route_polyline is None:
            body["locationBias"] = _circle(center, radius_km * 1000)
        if route_polyline:
            body["searchAlongRouteParameters"] = {"polyline": {"encodedPolyline": route_polyline}}
        if included_type:
            body["includedType"] = included_type
        if min_rating:
            body["minRating"] = min_rating
        if open_now:
            body["openNow"] = True
        if price_levels:
            body["priceLevels"] = [_PRICE_TO_GOOGLE[p] for p in price_levels]
        if rank_by_distance and route_polyline is None:
            body["rankPreference"] = "DISTANCE"

        data = await self._client.post(
            f"{BASE_URL}/places:searchText", body, field_mask=_mask(SEARCH_FIELDS, "places.")
        )
        places = [_to_place(p, center) for p in data.get("places", [])]
        places = _filter_places(
            places,
            min_reviews=min_reviews,
            radius_km=None if route_polyline else radius_km,
        )
        return places[:limit], len(places)

    async def nearby_search(
        self,
        *,
        center: Coordinates,
        radius_m: float,
        included_types: list[str],
        limit: int,
        rank_by_distance: bool = False,
        min_rating: float | None = None,
        min_reviews: int | None = None,
    ) -> tuple[list[Place], int]:
        body: dict[str, Any] = {
            "includedTypes": included_types,
            "maxResultCount": MAX_PAGE_SIZE,
            "locationRestriction": _circle(center, radius_m),
            "rankPreference": "DISTANCE" if rank_by_distance else "POPULARITY",
            **self._locale(),
        }
        data = await self._client.post(
            f"{BASE_URL}/places:searchNearby", body, field_mask=_mask(SEARCH_FIELDS, "places.")
        )
        places = [_to_place(p, center) for p in data.get("places", [])]
        if min_rating:
            places = [p for p in places if (p.rating or 0) >= min_rating]
        places = _filter_places(places, min_reviews=min_reviews, radius_km=None)
        return places[:limit], len(places)

    async def _get_place(self, place_id: str, fields: list[str]) -> dict[str, Any]:
        if not place_id or "/" in place_id or place_id.startswith("osm:"):
            raise ProviderError(T.Errors.INVALID_GOOGLE_PLACE_ID)
        return await self._client.get(
            f"{BASE_URL}/places/{place_id}",
            field_mask=_mask(fields),
            params=self._locale(),
        )

    async def details(self, place_id: str) -> PlaceDetails:
        raw = await self._get_place(place_id, DETAIL_FIELDS)
        base = _to_place(raw, None)
        hours = raw.get("regularOpeningHours") or {}
        amenities: dict[str, bool] = {key: bool(raw[key]) for key in _AMENITY_FIELDS if key in raw}
        for group in ("accessibilityOptions", "parkingOptions", "paymentOptions"):
            for key, value in (raw.get(group) or {}).items():
                if isinstance(value, bool):
                    amenities[key] = value
        reviews = [
            Review(
                rating=r.get("rating"),
                text=((r.get("text") or {}).get("text") or "")[:MAX_REVIEW_CHARS] or None,
                published=r.get("relativePublishTimeDescription"),
                author=(r.get("authorAttribution") or {}).get("displayName"),
                language=(r.get("text") or {}).get("languageCode"),
            )
            for r in raw.get("reviews", [])
        ]
        data = base.model_dump()
        data.update(
            description=(raw.get("editorialSummary") or {}).get("text"),
            website=raw.get("websiteUri"),
            phone=raw.get("nationalPhoneNumber"),
            opening_hours="; ".join(hours.get("weekdayDescriptions", [])) or None,
            opening_hours_weekdays=hours.get("weekdayDescriptions", []),
            utc_offset_minutes=raw.get("utcOffsetMinutes"),
            reviews=reviews,
            amenities=amenities,
            attribution=T.ATTRIBUTION,
        )
        return PlaceDetails(**data)

    async def opening_hours(self, place_id: str) -> dict[str, Any]:
        return await self._get_place(place_id, HOURS_FIELDS)
