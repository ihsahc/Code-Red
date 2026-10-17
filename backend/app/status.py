"""Turning a distance reading into a fill percentage and a status.

This is the core logic of the project, so it is kept separate from the
web and database code and is easy to test on its own.
"""

from datetime import datetime, timedelta
from enum import StrEnum

from app import config


class Status(StrEnum):
    FULL = "full"
    LOW = "low"
    EMPTY = "empty"
    OFFLINE = "offline"


# Lower number = more urgent. Used to sort the staff restock list.
URGENCY = {Status.EMPTY: 0, Status.OFFLINE: 1, Status.LOW: 2, Status.FULL: 3}


def fill_percent(distance_mm: float, empty_mm: float | None = None, full_mm: float | None = None) -> float:
    """Convert sensor distance to a fill percentage between 0 and 100.

    A full stack sits close to the sensor (small distance); an empty column
    leaves the sensor looking all the way down (large distance). Pass a
    dispenser's own calibration, or leave it out to use the defaults.
    """
    empty = empty_mm if empty_mm is not None else config.EMPTY_DISTANCE_MM
    full = full_mm if full_mm is not None else config.FULL_DISTANCE_MM
    percent = (empty - distance_mm) / (empty - full) * 100
    return round(max(0.0, min(100.0, percent)), 1)


def units_left(percent: float, empty_mm: float | None = None, full_mm: float | None = None) -> int:
    """Rough number of products left, for display ("about 7 left")."""
    empty = empty_mm if empty_mm is not None else config.EMPTY_DISTANCE_MM
    full = full_mm if full_mm is not None else config.FULL_DISTANCE_MM
    return round(percent / 100 * (empty - full) / config.PRODUCT_THICKNESS_MM)


def status_from_percent(percent: float) -> Status:
    if percent > config.FULL_ABOVE_PERCENT:
        return Status.FULL
    if percent < config.EMPTY_BELOW_PERCENT:
        return Status.EMPTY
    return Status.LOW


def current_status(percent: float | None, last_reading_at: datetime | None, now: datetime) -> Status:
    """Status shown in the app, including "offline" for silent sensors."""
    if percent is None or last_reading_at is None:
        return Status.OFFLINE
    if now - last_reading_at > timedelta(minutes=config.OFFLINE_AFTER_MINUTES):
        return Status.OFFLINE
    return status_from_percent(percent)
