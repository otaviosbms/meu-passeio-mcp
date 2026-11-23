from __future__ import annotations

from pydantic import BaseModel, Field

from meu_passeio.shared.schemas import TravelMode
from meu_passeio.texts import maps as T


class DistanceResult(BaseModel):
    straight_line_km: float
    method: str = "haversine"
    notes: list[str] = Field(default_factory=lambda: [T.Notes.STRAIGHT_LINE])


class TollInfo(BaseModel):
    has_tolls: bool | None = Field(default=None, description=T.Fields.HAS_TOLLS)
    estimated_price: float | None = Field(default=None, description=T.Fields.TOLL_PRICE)
    currency: str | None = None


class Leg(BaseModel):
    distance_meters: int
    duration_seconds: int


class Route(BaseModel):
    distance_meters: int
    duration_seconds: int = Field(description=T.Fields.DURATION)
    static_duration_seconds: int | None = Field(default=None, description=T.Fields.STATIC_DURATION)
    traffic_aware: bool = False
    description: str | None = Field(default=None, description=T.Fields.ROUTE_DESCRIPTION)
    warnings: list[str] = Field(default_factory=list)
    tolls: TollInfo = Field(default_factory=TollInfo)
    legs: list[Leg] = Field(default_factory=list)
    polyline: str | None = None


class RouteOptions(BaseModel):
    travel_mode: TravelMode
    departure_time: str | None = None
    routes: list[Route] = Field(description=T.Fields.ROUTES)
    source: str
    notes: list[str] = Field(default_factory=list)


class TollEstimate(BaseModel):
    has_tolls: bool | None
    outbound: TollInfo
    inbound: TollInfo | None = None
    total_estimated: float | None = Field(default=None, description=T.Fields.TOLL_TOTAL)
    currency: str | None = None
    outbound_route: str | None = None
    source: str
    notes: list[str] = Field(default_factory=list)


class TravelTimeMatrix(BaseModel):
    travel_mode: TravelMode
    durations_seconds: list[list[float | None]] = Field(description=T.Fields.DURATIONS)
    static_durations_seconds: list[list[float | None]] | None = None
    distances_meters: list[list[float | None]] | None = None
    traffic_aware: bool = False
    source: str
    notes: list[str] = Field(default_factory=list)


class OptimizedStops(BaseModel):
    order: list[int] = Field(description=T.Fields.ORDER)
    total_distance_meters: int
    total_duration_seconds: int
    legs: list[Leg] = Field(default_factory=list)
    roundtrip: bool
    travel_mode: TravelMode
    traffic_aware: bool = False
    source: str
    notes: list[str] = Field(default_factory=list)
