"""Code Red API: tampon dispenser fill levels across Georgia Tech.

Run locally (from the backend folder):
    uvicorn app.main:app --reload
Then open http://localhost:8000/docs to try every endpoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import config
from app.database import Base, SessionLocal, add_missing_columns, engine
from app.routers import dispensers, readings, staff
from app.seed import seed_if_empty
from app.services import sync_real_dispenser

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist yet, and add any new columns to
    # tables that do. Fine for a hackathon; a bigger project would use
    # migrations (Alembic) instead.
    Base.metadata.create_all(engine)
    for added in add_missing_columns(engine):
        log.info("Added database column %s", added)
    if config.SEED_DEMO_DATA:
        seed_if_empty()
    with SessionLocal() as db:
        log.info(sync_real_dispenser(db))
    yield


app = FastAPI(
    title="Code Red API",
    description="Live fill levels for tampon dispensers across Georgia Tech's campus.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dispensers.router)
app.include_router(staff.router)
app.include_router(readings.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health():
    """Quick check that the server is up. Render uses this too."""
    return {"ok": True}
