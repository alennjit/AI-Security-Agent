"""Pydantic request/response schemas for the events API."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    host: str
    provider: str
    surface: str
    risk_score: int = Field(ge=1, le=10)
    rationale: str
    categories: list[str]
    finding_count: int = Field(ge=0)
    client_ip: str | None = Field(default=None, max_length=64)


class EventRead(EventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime
