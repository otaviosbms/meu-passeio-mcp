from __future__ import annotations

from pydantic import BaseModel, Field

from meu_passeio.shared.schemas import Coordinates, Waypoint
from meu_passeio.texts import planning as T


class Attraction(BaseModel):
    id: str
    name: str
    category_label: str | None = None
    rating: float | None = None
    user_rating_count: int | None = None
    coordinates: Coordinates | None = None
    google_maps_uri: str | None = None


class DayTripDestination(BaseModel):
    town: str
    state_code: str | None = None
    drive_minutes: int = Field(description=T.Fields.DRIVE_MINUTES)
    drive_minutes_no_traffic: int | None = None
    distance_km: float | None = None
    score: float = Field(description=T.Fields.SCORE)
    attraction_count: int
    top_attractions: list[Attraction]


class DayTripSuggestions(BaseModel):
    origin: Coordinates
    origin_label: str | None = None
    max_drive_hours: float
    destinations: list[DayTripDestination]
    candidates_considered: int
    source: str = "google_maps"
    attribution: str
    notes: list[str] = Field(default_factory=list)


class DayStop(BaseModel):
    place: Waypoint = Field(description=T.Params.STOP_PLACE)
    name: str | None = Field(default=None, description=T.Params.STOP_NAME)
    visit_minutes: int = Field(default=60, ge=10, le=600, description=T.Params.VISIT_MINUTES)


class ScheduledStop(BaseModel):
    order: int
    input_index: int = Field(description=T.Fields.INPUT_INDEX)
    name: str
    place_id: str | None = None
    arrival: str = Field(description=T.Fields.CLOCK)
    visit_start: str
    departure: str
    travel_minutes_from_previous: int
    distance_km_from_previous: float
    wait_minutes: int = 0
    is_open_on_arrival: bool | None = None
    closes_at: str | None = None
    warnings: list[str] = Field(default_factory=list)


class DayItinerary(BaseModel):
    date: str
    start_time: str
    end_arrival: str = Field(description=T.Fields.END_ARRIVAL)
    stops: list[ScheduledStop]
    total_travel_minutes: int
    total_distance_km: float
    total_visit_minutes: int
    order_optimized: bool
    traffic_aware: bool
    source: str
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
