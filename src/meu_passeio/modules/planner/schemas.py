"""Schemas de saída estruturada do planner (validados pelo SDK e pela aplicação)."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from meu_passeio.shared.schemas import Transportation, TripPlan

TripType = Literal["day_trip", "weekend", "vacation", "road_trip", "other"]


class ParsedBudget(BaseModel):
    amount: float
    currency: Literal["BRL"] = "BRL"
    excluded_categories: list[str] = Field(
        default_factory=list, description="ex.: accommodation, transport"
    )


class TripRequest(BaseModel):
    """Requisitos extraídos da mensagem do usuário pelo Request Parser."""

    trip_type: TripType
    origin: str | None = Field(default=None, description="Cidade de partida, se informada")
    destination: str | None = Field(
        default=None, description="Destino, ou null se o usuário quer sugestões a partir da origem"
    )
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    duration_days: int | None = Field(default=None, description="Número de dias (bate-volta = 1)")
    travelers: int = 1
    transportation: Transportation = "car"
    max_travel_hours: float | None = Field(
        default=None, description="Tempo máximo de deslocamento a partir da origem, em horas"
    )
    budget: ParsedBudget | None = None
    preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list, description="Restrições adicionais")
    assumptions: list[str] = Field(
        default_factory=list, description="Suposições feitas na interpretação (ex.: ano das datas)"
    )
    clarification_questions: list[str] = Field(
        default_factory=list,
        description="Perguntas somente sobre informações ESSENCIAIS que faltam",
    )


class ItineraryOutput(BaseModel):
    """Itinerário final gerado pelo Itinerary Builder."""

    plan: TripPlan
    summary: str = Field(description="Resumo curto do roteiro, em português")
