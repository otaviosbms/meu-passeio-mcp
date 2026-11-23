from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from meu_passeio.db.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: f"trip_{uuid.uuid4().hex[:12]}"
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    request_text: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    trip_request: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    revisions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    last_run_id: Mapped[str | None] = mapped_column(String(40))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
