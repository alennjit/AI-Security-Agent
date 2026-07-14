"""Ingestion and retrieval API for DLP events raised by the proxy addon."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event
from app.schemas import EventCreate, EventRead

logger = logging.getLogger("ai_security_agent.backend")

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=201)
def create_event(event_in: EventCreate, db: Session = Depends(get_db)) -> Event:
    """Record a DLP finding raised by the proxy addon.

    The proxy is responsible for redacting matched values before this ever
    gets called — this endpoint trusts the payload contains no raw secrets,
    but never logs the raw request body, only the fact that an event was
    recorded, to stay consistent with that guarantee.
    """
    event = Event(**event_in.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(
        "Recorded event id=%s host=%s risk_score=%s", event.id, event.host, event.risk_score
    )
    return event


@router.get("", response_model=list[EventRead])
def list_events(
    min_risk: int = Query(default=1, ge=1, le=10),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[Event]:
    stmt = (
        select(Event)
        .where(Event.risk_score >= min_risk)
        .order_by(Event.created_at.desc(), Event.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
