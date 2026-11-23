from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from meu_passeio.shared.schemas import TripPlan


class TripWrite(BaseModel):
    """Corpo de criação/atualização: o roteiro é montado pelo cliente."""

    title: str | None = Field(default=None, max_length=255)
    plan: TripPlan


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None
    plan: TripPlan
    created_at: datetime
    updated_at: datetime


class TripListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
