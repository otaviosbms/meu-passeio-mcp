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
    "hiking_area",
    "tourist_attraction",
    "museum",
    "art_gallery",
    "historic",
    "theatre",
    "zoo",
    "aquarium",
    "theme_park",
    "place_of_worship",
    "shopping_mall",
    "restaurant",
    "cafe",
    "bar",
]

FoodCategory = Literal["restaurant", "cafe", "bar", "bakery", "fast_food", "ice_cream"]
PriceLevel = Literal["free", "inexpensive", "moderate", "expensive", "very_expensive"]
RankBy = Literal["relevance", "distance", "popularity"]


class PriceRange(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str | None = None


class Review(BaseModel):
    rating: float | None = None
    text: str | None = None
    published: str | None = Field(default=None, description=T.Fields.REVIEW_PUBLISHED)
    author: str | None = None
    language: str | None = None


class Place(BaseModel):
    id: str = Field(description=T.Fields.ID)
    name: str
    category: str | None = None
    category_label: str | None = None
    description: str | None = None
    address: str | None = None
    coordinates: Coordinates | None = None
    distance_km: float | None = Field(default=None, description=T.Fields.DISTANCE_KM)
    rating: float | None = Field(default=None, description=T.Fields.RATING)
    user_rating_count: int | None = Field(default=None, description=T.Fields.USER_RATING_COUNT)
    price_level: PriceLevel | None = Field(default=None, description=T.Fields.PRICE_LEVEL)
    price_range: PriceRange | None = Field(default=None, description=T.Fields.PRICE_RANGE)
    open_now: bool | None = None
    business_status: str | None = None
    opening_hours: str | None = Field(default=None, description=T.Fields.OPENING_HOURS)
    cuisine: str | None = None
    website: str | None = None
    google_maps_uri: str | None = None
    source: str = T.Sources.OSM


class PlaceSearchResult(BaseModel):
    center: Coordinates | None = None
    resolved_location: str | None = None
    radius_km: float | None = None
    places: list[Place]
    total_found: int
    source: str = T.Sources.OSM
    attribution: str | None = None
    notes: list[str] = Field(default_factory=list)


class PlaceDetails(Place):
    phone: str | None = None
    wheelchair: str | None = None
    opening_hours_weekdays: list[str] = Field(default_factory=list)
    utc_offset_minutes: int | None = None
    reviews: list[Review] = Field(default_factory=list, description=T.Fields.REVIEWS)
    amenities: dict[str, bool] = Field(default_factory=dict, description=T.Fields.AMENITIES)
    tags: dict[str, str] = Field(default_factory=dict, description=T.Fields.TAGS)
    attribution: str | None = None


class OpeningCheck(BaseModel):
    place_id: str
    name: str | None = None
    datetime_local: str
    is_open: bool | None = Field(description=T.Fields.IS_OPEN)
    opens_at: str | None = None
    closes_at: str | None = None
    opening_hours_weekdays: list[str] = Field(default_factory=list)
    business_status: str | None = None
    source: str
    notes: list[str] = Field(default_factory=list)
