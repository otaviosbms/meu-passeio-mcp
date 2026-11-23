from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from meu_passeio.shared.schemas import Coordinates
from meu_passeio.texts import places as T

PlaceCategory = Literal[
    "park",
    "nature_reserve",
    "viewpoint",
    "waterfall",
    "beach",
    "tourist_attraction",
    "museum",
    "art_gallery",
    "historic",
    "theatre",
    "zoo",
    "theme_park",
    "place_of_worship",
    "shopping_mall",
    "restaurant",
    "cafe",
    "bar",
]

FoodCategory = Literal["restaurant", "cafe", "bar", "fast_food", "ice_cream"]


class Place(BaseModel):
    id: str = Field(description=T.Fields.ID)
    name: str
    category: str | None = None
    description: str | None = None
    address: str | None = None
    coordinates: Coordinates | None = None
    distance_km: float | None = Field(default=None, description=T.Fields.DISTANCE_KM)
    rating: float | None = Field(default=None, description=T.Fields.RATING)
    price_level: int | None = None
    opening_hours: str | None = Field(default=None, description=T.Fields.OPENING_HOURS)
    cuisine: str | None = None
    website: str | None = None
    source: str = T.Sources.OSM


class PlaceSearchResult(BaseModel):
    center: Coordinates
    resolved_location: str | None = None
    radius_km: float
    places: list[Place]
    total_found: int
    source: str = T.Sources.OSM
    notes: list[str] = Field(default_factory=list)


class PlaceDetails(Place):
    phone: str | None = None
    wheelchair: str | None = None
    tags: dict[str, str] = Field(default_factory=dict, description=T.Fields.TAGS)
