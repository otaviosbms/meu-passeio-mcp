"""Schemas de domínio compartilhados entre API, planner e MCP Servers."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TravelMode = Literal["driving", "walking", "cycling"]
Transportation = Literal["car", "bus", "plane", "walking", "other"]


class Coordinates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Budget(BaseModel):
    total: float = Field(ge=0)
    currency: Literal["BRL"] = "BRL"
    excluded_categories: list[str] = Field(default_factory=list)


class TripActivity(BaseModel):
    id: str
    place_id: str | None = None
    name: str
    category: str | None = None
    description: str | None = None
    start_time: str | None = Field(default=None, description="HH:MM, horário sugerido")
    duration_minutes: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    location: Coordinates | None = None
    source: str | None = None
    notes: list[str] = Field(default_factory=list)


class TripDay(BaseModel):
    date: dt.date | None = None
    day_number: int = Field(ge=1)
    title: str | None = None
    weather_summary: str | None = None
    activities: list[TripActivity] = Field(default_factory=list)


class CostEstimate(BaseModel):
    category: str
    amount: float = Field(ge=0)
    notes: str | None = None


class TripPlan(BaseModel):
    title: str | None = None
    origin: str | None = None
    destination: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    travelers: int = Field(default=1, ge=1)
    transportation: Transportation = "car"
    budget: Budget | None = None
    preferences: list[str] = Field(default_factory=list)
    itinerary: list[TripDay] = Field(default_factory=list)
    cost_estimates: list[CostEstimate] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
