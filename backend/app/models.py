"""Database tables.

Building  1 ── many  Dispenser  1 ── many  Reading
                               1 ── many  Alert
"""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.timeutil import utcnow


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    dispensers: Mapped[list["Dispenser"]] = relationship(back_populates="building")


class Dispenser(Base):
    __tablename__ = "dispensers"

    # A readable ID such as "klaus-2f-w", also used by the device when it reports.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    floor: Mapped[str] = mapped_column(String(20))
    # Where in the building, e.g. "Women's restroom by the east stairs".
    location_note: Mapped[str] = mapped_column(String(200), default="")
    # Secret the device sends with each reading, so nobody else can fake one.
    device_key: Mapped[str] = mapped_column(String(64))
    # True for the physical dispenser; False/None for simulated ones.
    is_real: Mapped[bool | None] = mapped_column(nullable=True)
    # Per-dispenser calibration. When empty, the defaults in config.py apply.
    empty_distance_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    full_distance_mm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Latest values, copied from the newest reading so lists load quickly.
    last_distance_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_fill_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_reading_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_refill_at: Mapped[datetime | None] = mapped_column(nullable=True)

    building: Mapped[Building] = relationship(back_populates="dispensers")
    readings: Mapped[list["Reading"]] = relationship(back_populates="dispenser")


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dispenser_id: Mapped[str] = mapped_column(ForeignKey("dispensers.id"), index=True)
    distance_mm: Mapped[float] = mapped_column(Float)
    fill_percent: Mapped[float] = mapped_column(Float)
    battery_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    dispenser: Mapped[Dispenser] = relationship(back_populates="readings")


class Alert(Base):
    """Raised when a dispenser drops to "low" or "empty"; resolved on refill."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dispenser_id: Mapped[str] = mapped_column(ForeignKey("dispensers.id"), index=True)
    level: Mapped[str] = mapped_column(String(10))  # "low" or "empty"
    fill_percent: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    dispenser: Mapped[Dispenser] = relationship()
