from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from meu_passeio.shared.schemas import TripPlan


class CreateTripRequest(BaseModel):
    request: str = Field(
        min_length=5,
        max_length=4000,
        examples=[
            "Quero um bate-volta saindo de Marília, até duas horas de carro, com natureza e "
            "orçamento de R$ 400."
        ],
    )


class ClarifyTripRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class ReviseTripRequest(BaseModel):
    instruction: str = Field(
        min_length=3,
        max_length=2000,
        examples=["Troque o jantar do dia 2 por um restaurante italiano."],
    )


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    title: str | None
    request_text: str
    summary: str | None
    trip_request: dict[str, Any] | None
    plan: TripPlan | None
    questions: list[str]
    warnings: list[str]
    revisions: list[dict[str, Any]]
    last_run_id: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class TripListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    title: str | None
    created_at: datetime
    updated_at: datetime
