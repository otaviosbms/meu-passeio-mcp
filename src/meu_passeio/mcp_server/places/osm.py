"""Provider de lugares baseado em OpenStreetMap (Nominatim + Overpass), sem API key.

O provider só retorna dados que vieram do OSM. Campos que o OSM não fornece
(ex.: avaliação) são devolvidos como ``None`` — nunca inventados.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx

from meu_passeio.mcp_server.common.geo import haversine_km
from meu_passeio.mcp_server.common.http import ProviderError, get_json, post_form_json
from meu_passeio.mcp_server.places.schemas import Place, PlaceDetails
from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import places as T
from meu_passeio.texts.common import ProviderErrors

NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
# Instâncias públicas do Overpass costumam oscilar (429/502/504): tentamos em sequência.
OVERPASS_URLS = [
    url.strip()
    for url in os.getenv(
        "OVERPASS_URLS",
        "https://overpass-api.de/api/interpreter,"
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter,"
        "https://overpass.private.coffee/api/interpreter",
    ).split(",")
    if url.strip()
]
OVERPASS_TIMEOUT_SECONDS = float(os.getenv("OVERPASS_TIMEOUT_SECONDS", "20"))
OVERPASS_COOLDOWN_SECONDS = float(os.getenv("OVERPASS_COOLDOWN_SECONDS", "120"))

# Fallback quando nenhuma instância Overpass responde: busca textual no Nominatim
# (special phrases), que retorna menos dados, mas mantém o server útil.
NOMINATIM_FALLBACK_TERMS: dict[str, str] = {
    "park": "park",
    "nature_reserve": "nature reserve",
    "viewpoint": "viewpoint",
    "waterfall": "waterfall",
    "beach": "beach",
    "tourist_attraction": "attraction",
    "museum": "museum",
    "art_gallery": "gallery",
    "historic": "monument",
    "theatre": "theatre",
    "zoo": "zoo",
    "theme_park": "theme park",
    "place_of_worship": "church",
    "shopping_mall": "mall",
    "restaurant": "restaurant",
    "cafe": "cafe",
    "bar": "bar",
    "fast_food": "fast food",
    "ice_cream": "ice cream",
    "hiking_area": "trailhead",
    "aquarium": "aquarium",
    "bakery": "bakery",
}

# Categoria -> filtros de tags do Overpass
CATEGORY_FILTERS: dict[str, list[str]] = {
    "park": ['["leisure"="park"]'],
    "nature_reserve": ['["leisure"="nature_reserve"]', '["boundary"="protected_area"]'],
    "viewpoint": ['["tourism"="viewpoint"]'],
    "waterfall": ['["waterway"="waterfall"]'],
    "beach": ['["natural"="beach"]'],
    "tourist_attraction": ['["tourism"="attraction"]'],
    "museum": ['["tourism"="museum"]'],
    "art_gallery": ['["tourism"="gallery"]'],
    "historic": ['["historic"~"^(monument|memorial|castle|ruins|fort|building)$"]'],
    "theatre": ['["amenity"="theatre"]'],
    "zoo": ['["tourism"="zoo"]'],
    "theme_park": ['["tourism"="theme_park"]'],
    "place_of_worship": ['["amenity"="place_of_worship"]'],
    "shopping_mall": ['["shop"="mall"]'],
    "restaurant": ['["amenity"="restaurant"]'],
    "cafe": ['["amenity"="cafe"]'],
    "bar": ['["amenity"~"^(bar|pub)$"]'],
    "fast_food": ['["amenity"="fast_food"]'],
    "ice_cream": ['["amenity"="ice_cream"]'],
    "hiking_area": ['["highway"="trailhead"]', '["route"="hiking"]'],
    "aquarium": ['["tourism"="aquarium"]'],
    "bakery": ['["shop"="bakery"]'],
}

_TAG_TO_CATEGORY: list[tuple[str, str, str]] = [
    ("amenity", "restaurant", "restaurant"),
    ("amenity", "cafe", "cafe"),
    ("amenity", "bar", "bar"),
    ("amenity", "pub", "bar"),
    ("amenity", "fast_food", "fast_food"),
    ("amenity", "ice_cream", "ice_cream"),
    ("tourism", "aquarium", "aquarium"),
    ("shop", "bakery", "bakery"),
    ("highway", "trailhead", "hiking_area"),
    ("amenity", "theatre", "theatre"),
    ("amenity", "place_of_worship", "place_of_worship"),
    ("tourism", "museum", "museum"),
    ("tourism", "gallery", "art_gallery"),
    ("tourism", "viewpoint", "viewpoint"),
    ("tourism", "zoo", "zoo"),
    ("tourism", "theme_park", "theme_park"),
    ("tourism", "attraction", "tourist_attraction"),
    ("leisure", "park", "park"),
    ("leisure", "nature_reserve", "nature_reserve"),
    ("boundary", "protected_area", "nature_reserve"),
    ("waterway", "waterfall", "waterfall"),
    ("natural", "beach", "beach"),
    ("shop", "mall", "shopping_mall"),
]

_DETAIL_TAGS = {
    "opening_hours",
    "website",
    "contact:website",
    "phone",
    "contact:phone",
    "cuisine",
    "wheelchair",
    "description",
    "fee",
    "charge",
    "operator",
    "wikipedia",
    "wikidata",
    "outdoor_seating",
    "diet:vegetarian",
    "diet:vegan",
    "takeaway",
    "reservation",
}


def _category_from_tags(tags: dict[str, str]) -> str | None:
    for key, value, category in _TAG_TO_CATEGORY:
        if tags.get(key) == value:
            return category
    if "historic" in tags:
        return "historic"
    return None


def _address_from_tags(tags: dict[str, str]) -> str | None:
    street = tags.get("addr:street")
    number = tags.get("addr:housenumber")
    parts = [
        f"{street}, {number}" if street and number else street,
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:state"),
    ]
    joined = " - ".join(p for p in parts if p)
    return joined or None


def _element_coordinates(element: dict[str, Any]) -> Coordinates | None:
    if "lat" in element and "lon" in element:
        return Coordinates(latitude=element["lat"], longitude=element["lon"])
    center = element.get("center")
    if center:
        return Coordinates(latitude=center["lat"], longitude=center["lon"])
    return None


def _element_to_place(element: dict[str, Any], center: Coordinates | None) -> Place | None:
    tags: dict[str, str] = element.get("tags", {})
    name = tags.get("name")
    if not name:
        return None
    coords = _element_coordinates(element)
    distance = (
        round(haversine_km(center.latitude, center.longitude, coords.latitude, coords.longitude), 2)
        if center and coords
        else None
    )
    return Place(
        id=f"osm:{element['type']}:{element['id']}",
        name=name,
        category=_category_from_tags(tags),
        description=tags.get("description"),
        address=_address_from_tags(tags),
        coordinates=coords,
        distance_km=distance,
        opening_hours=tags.get("opening_hours"),
        cuisine=tags.get("cuisine"),
        website=tags.get("website") or tags.get("contact:website"),
    )


def _escape_overpass_regex(text: str) -> str:
    return re.sub(r'([\\"])', r"\\\1", re.escape(text))


class OsmPlacesProvider:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._overpass_open_until = 0.0

    async def geocode(self, location: str) -> tuple[Coordinates, str]:
        data = await get_json(
            self._client,
            f"{NOMINATIM_URL}/search",
            params={"q": location, "format": "jsonv2", "limit": 1, "accept-language": "pt-BR"},
            provider="nominatim",
        )
        if not data:
            raise ProviderError(ProviderErrors.LOCATION_NOT_FOUND.format(location=location))
        first = data[0]
        return (
            Coordinates(latitude=float(first["lat"]), longitude=float(first["lon"])),
            first.get("display_name", location),
        )

    async def resolve_center(
        self, location: str | None, coordinates: Coordinates | None
    ) -> tuple[Coordinates, str | None]:
        if coordinates is not None:
            return coordinates, None
        if not location:
            raise ProviderError(T.Errors.MISSING_LOCATION)
        return await self.geocode(location)

    async def _overpass(self, query: str) -> list[dict[str, Any]]:
        # Circuit breaker: se todas as instâncias falharam há pouco, nem tenta (vai direto ao
        # fallback) — evita que cada chamada espere N × timeout enquanto o Overpass está fora.
        if time.monotonic() < self._overpass_open_until:
            raise ProviderError(T.Errors.OVERPASS_CIRCUIT_OPEN)
        last_error: ProviderError | None = None
        for url in OVERPASS_URLS:
            try:
                data = await post_form_json(
                    self._client,
                    url,
                    data={"data": query},
                    provider="overpass",
                    timeout=OVERPASS_TIMEOUT_SECONDS,
                )
                return data.get("elements", [])
            except ProviderError as exc:
                last_error = exc
        self._overpass_open_until = time.monotonic() + OVERPASS_COOLDOWN_SECONDS
        raise last_error or ProviderError(T.Errors.OVERPASS_NOT_CONFIGURED)

    async def search_by_categories(
        self,
        *,
        center: Coordinates,
        categories: list[str],
        radius_km: float,
        limit: int,
        name_contains: str | None = None,
        cuisine: str | None = None,
    ) -> tuple[list[Place], int]:
        radius_m = int(radius_km * 1000)
        name_filter = (
            f'["name"~"{_escape_overpass_regex(name_contains)}",i]' if name_contains else '["name"]'
        )
        cuisine_filter = f'["cuisine"~"{_escape_overpass_regex(cuisine)}",i]' if cuisine else ""
        statements = []
        for category in categories:
            for tag_filter in CATEGORY_FILTERS.get(category, []):
                statements.append(
                    f"nwr{tag_filter}{name_filter}{cuisine_filter}"
                    f"(around:{radius_m},{center.latitude},{center.longitude});"
                )
        if not statements:
            raise ProviderError(T.Errors.NO_VALID_CATEGORY)
        timeout = int(OVERPASS_TIMEOUT_SECONDS)
        query = f"[out:json][timeout:{timeout}];({''.join(statements)});out center tags 200;"
        try:
            elements = await self._overpass(query)
        except ProviderError:
            if cuisine or name_contains:
                raise
            return await self._fallback_search(center, categories, radius_km, limit)

        seen: set[str] = set()
        places: list[Place] = []
        for element in elements:
            place = _element_to_place(element, center)
            if place is None:
                continue
            dedupe_key = f"{place.name.lower()}|{place.category}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            places.append(place)
        places.sort(key=lambda p: p.distance_km if p.distance_km is not None else float("inf"))
        return places[:limit], len(places)

    async def _fallback_search(
        self, center: Coordinates, categories: list[str], radius_km: float, limit: int
    ) -> tuple[list[Place], int]:
        places: dict[str, Place] = {}
        for category in categories:
            term = NOMINATIM_FALLBACK_TERMS.get(category)
            if not term:
                continue
            found, _ = await self.search_by_text(
                query=term, center=center, radius_km=radius_km, limit=limit
            )
            for place in found:
                place.category = category
                place.source = T.Sources.NOMINATIM_FALLBACK
                places.setdefault(place.id, place)
        ordered = sorted(places.values(), key=lambda p: p.distance_km or 0)
        return ordered[:limit], len(ordered)

    async def search_by_text(
        self, *, query: str, center: Coordinates, radius_km: float, limit: int
    ) -> tuple[list[Place], int]:
        # viewbox ~ quadrado em torno do centro (1 grau ≈ 111 km)
        delta = radius_km / 111.0
        viewbox = (
            f"{center.longitude - delta},{center.latitude + delta},"
            f"{center.longitude + delta},{center.latitude - delta}"
        )
        data = await get_json(
            self._client,
            f"{NOMINATIM_URL}/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": min(limit * 2, 40),
                "viewbox": viewbox,
                "bounded": 1,
                "extratags": 1,
                "addressdetails": 0,
                "accept-language": "pt-BR",
            },
            provider="nominatim",
        )
        places: list[Place] = []
        for item in data:
            name = item.get("name") or (item.get("display_name") or "").split(",")[0]
            if not name:
                continue
            lat, lon = float(item["lat"]), float(item["lon"])
            extratags = item.get("extratags") or {}
            places.append(
                Place(
                    id=f"osm:{item.get('osm_type', 'node')}:{item.get('osm_id')}",
                    name=name,
                    category=item.get("type"),
                    address=item.get("display_name"),
                    coordinates=Coordinates(latitude=lat, longitude=lon),
                    distance_km=round(haversine_km(center.latitude, center.longitude, lat, lon), 2),
                    opening_hours=extratags.get("opening_hours"),
                    website=extratags.get("website"),
                )
            )
        places.sort(key=lambda p: p.distance_km or 0)
        return places[:limit], len(places)

    async def details(self, place_id: str) -> PlaceDetails:
        match = re.fullmatch(r"osm:(node|way|relation):(\d+)", place_id)
        if not match:
            raise ProviderError(T.Errors.INVALID_PLACE_ID)
        osm_type, osm_id = match.groups()
        try:
            elements = await self._overpass(
                f"[out:json][timeout:{int(OVERPASS_TIMEOUT_SECONDS)}];"
                f"{osm_type}({osm_id});out center tags;"
            )
        except ProviderError:
            return await self._details_via_nominatim(place_id, osm_type, osm_id)
        if not elements:
            raise ProviderError(T.Errors.PLACE_NOT_FOUND.format(place_id=place_id))
        element = elements[0]
        tags: dict[str, str] = element.get("tags", {})
        base = _element_to_place(element, None)
        if base is None:
            raise ProviderError(T.Errors.PLACE_WITHOUT_NAME.format(place_id=place_id))
        return PlaceDetails(
            **base.model_dump(),
            phone=tags.get("phone") or tags.get("contact:phone"),
            wheelchair=tags.get("wheelchair"),
            tags={k: v for k, v in tags.items() if k in _DETAIL_TAGS},
        )

    async def _details_via_nominatim(
        self, place_id: str, osm_type: str, osm_id: str
    ) -> PlaceDetails:
        data = await get_json(
            self._client,
            f"{NOMINATIM_URL}/lookup",
            params={
                "osm_ids": f"{osm_type[0].upper()}{osm_id}",
                "format": "jsonv2",
                "extratags": 1,
                "accept-language": "pt-BR",
            },
            provider="nominatim",
        )
        if not data:
            raise ProviderError(T.Errors.PLACE_NOT_FOUND.format(place_id=place_id))
        item = data[0]
        extratags: dict[str, str] = item.get("extratags") or {}
        name = item.get("name") or (item.get("display_name") or "").split(",")[0]
        return PlaceDetails(
            id=place_id,
            name=name,
            category=item.get("type"),
            description=extratags.get("description"),
            address=item.get("display_name"),
            coordinates=Coordinates(latitude=float(item["lat"]), longitude=float(item["lon"])),
            opening_hours=extratags.get("opening_hours"),
            cuisine=extratags.get("cuisine"),
            website=extratags.get("website") or extratags.get("contact:website"),
            phone=extratags.get("phone") or extratags.get("contact:phone"),
            wheelchair=extratags.get("wheelchair"),
            tags={k: v for k, v in extratags.items() if k in _DETAIL_TAGS},
            source=T.Sources.NOMINATIM_FALLBACK,
        )
