"""Shapes of the data going in and out of the API.

FastAPI uses these to validate requests and to build the docs at /docs.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.status import Status


class BuildingOut(BaseModel):
    id: int
    name: str
    lat: float
    lng: float


class DispenserOut(BaseModel):
    id: str
    building: BuildingOut
    floor: str
    location_note: str
    real: bool = Field(description="True for the physical dispenser, false for simulated ones")
    status: Status
    fill_percent: float | None = Field(description="0–100, or null if no reading yet")
    units_left: int | None = Field(description="Rough count of products left")
    last_reading_at: datetime | None
    last_refill_at: datetime | None


class NearbyDispenserOut(DispenserOut):
    distance_m: int = Field(description="Straight-line distance from the user, in metres")


class ReadingIn(BaseModel):
    """What a dispenser's sensor sends every few minutes."""

    dispenser_id: str = Field(examples=["klaus-2f-w"])
    distance_mm: float = Field(ge=0, le=2000, description="Median of several VL53L0X readings")
    battery_v: float | None = Field(default=None, ge=0, le=10)


class ReadingAccepted(BaseModel):
    dispenser_id: str
    fill_percent: float
    status: Status


class ReadingOut(BaseModel):
    distance_mm: float
    fill_percent: float
    created_at: datetime


class NearestIn(BaseModel):
    """The user's location. Used for this one request only and never stored."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    limit: int = Field(default=3, ge=1, le=20)


class AlertOut(BaseModel):
    id: int
    dispenser_id: str
    building_name: str
    floor: str
    location_note: str
    level: Status
    fill_percent: float
    created_at: datetime
    resolved_at: datetime | None
