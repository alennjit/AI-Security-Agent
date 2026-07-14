"""FastAPI entry point for the AI Security Agent backend."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.events import router as events_router
from app.db import Base, engine

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Security Agent", lifespan=lifespan)
app.include_router(events_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
