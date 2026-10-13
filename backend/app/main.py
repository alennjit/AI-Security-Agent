"""FastAPI entry point for the AI Security Agent backend."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.events import router as events_router
from app.db import Base, engine

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Security Agent", lifespan=lifespan)

# Dashboard origins allowed to call the API. Defaults to the Vite dev server;
# override with AISA_CORS_ORIGINS (comma-separated). Tighten when auth and a real deployment exist.
_DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [o.strip() for o in os.environ.get("AISA_CORS_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(events_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
