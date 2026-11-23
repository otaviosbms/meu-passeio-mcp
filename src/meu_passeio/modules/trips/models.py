from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from meu_passeio.db.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: f"trip_{uuid.uuid4().hex[:12]}"
    )
    title: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
