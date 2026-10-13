"""SQLAlchemy models for ingested DLP events.

Deliberately does not store raw prompt text or raw matched secret/PII
values (see CLAUDE.md, docs/PRIVACY_AND_CONSENT.md) — only the
already-redacted summary the proxy addon produces.
"""

from __future__ import annotations

import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host: Mapped[str] = mapped_column(String, index=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    surface: Mapped[str] = mapped_column(String)
    risk_score: Mapped[int] = mapped_column(Integer, index=True)
    rationale: Mapped[str] = mapped_column(String)
    categories: Mapped[list[str]] = mapped_column(JSON)
    finding_count: Mapped[int] = mapped_column(Integer)
    client_ip: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=_utcnow, index=True
    )
