"""Logic shared by several endpoints: recording readings, raising alerts,
and turning database rows into API responses."""

import hashlib
import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import Alert, Dispenser, Reading
from app.schemas import AlertOut, BuildingOut, DispenserOut
from app.status import (
    Status,
    current_status,
    fill_percent,
    percent_from_units,
    status_from_percent,
    units_from_levels,
    units_left,
)
from app.timeutil import to_utc, utcnow


MAX_DEMO_STREAK_DAYS = 31


def is_simulated(d: Dispenser) -> bool:
    """True for the demo dispensers; False for the real Pico W box."""
    return not d.is_real and d.id != config.REAL_DISPENSER_ID


def demo_streak_days(dispenser_id: str) -> int:
    """A made-up but stable streak length (1-31 days) for a simulated dispenser.

    Real streaks only grow one day per day, so a fresh demo would show 0 everywhere.
    Hashing the ID gives each simulated dispenser its own believable history that
    stays the same across restarts.
    """
    return int(hashlib.sha256(dispenser_id.encode()).hexdigest(), 16) % MAX_DEMO_STREAK_DAYS + 1


def demo_streak_start(dispenser_id: str, now):
    """When a simulated dispenser's made-up streak began."""
    return now - timedelta(days=demo_streak_days(dispenser_id), hours=3)


def counts_by_level(d: Dispenser) -> bool:
    """The real box is counted with its measured levels (REAL_LEVELS_MM in config)."""
    return bool(d.is_real) and bool(config.REAL_LEVELS_MM)


def reading_fill_percent(d: Dispenser, distance_mm: float) -> float:
    """Fill percentage for one reading from this dispenser."""
    if counts_by_level(d):
        units = units_from_levels(distance_mm, config.REAL_LEVELS_MM, config.REAL_COLUMN_EMPTY_MM, config.REAL_CAPACITY)
        return percent_from_units(units, config.REAL_CAPACITY)
    return fill_percent(distance_mm, d.empty_distance_mm, d.full_distance_mm)


def display_units_left(d: Dispenser, pct: float | None) -> int | None:
    """Products left for the API. For the real box this is an exact count
    (or "this many or fewer" once its column is empty)."""
    if pct is None:
        return None
    if counts_by_level(d):
        return round(pct / 100 * config.REAL_CAPACITY)
    return units_left(pct, d.empty_distance_mm, d.full_distance_mm)


def streak_days(d: Dispenser, status: Status, now) -> int | None:
    """Days since the dispenser was last empty: 0 while empty, None if unknown."""
    if status == Status.EMPTY:
        return 0
    if d.streak_started_at is None:
        return None
    return max(0, (now - d.streak_started_at).days)


def dispenser_out(d: Dispenser, now=None) -> DispenserOut:
    now = now or utcnow()
    pct = d.last_fill_percent
    status = current_status(pct, d.last_reading_at, now)
    return DispenserOut(
        id=d.id,
        building=BuildingOut(id=d.building.id, name=d.building.name, lat=d.building.lat, lng=d.building.lng),
        floor=d.floor,
        location_note=d.location_note,
        real=bool(d.is_real),
        status=status,
        fill_percent=pct,
        units_left=display_units_left(d, pct),
        last_reading_at=to_utc(d.last_reading_at),
        last_refill_at=to_utc(d.last_refill_at),
        streak_days=streak_days(d, status, now),
        streak_started_at=to_utc(d.streak_started_at),
    )


def alert_out(a: Alert) -> AlertOut:
    d = a.dispenser
    return AlertOut(
        id=a.id,
        dispenser_id=d.id,
        building_name=d.building.name,
        floor=d.floor,
        location_note=d.location_note,
        level=Status(a.level),
        fill_percent=a.fill_percent,
        created_at=to_utc(a.created_at),
        resolved_at=to_utc(a.resolved_at),
    )


def record_reading(
    db: Session,
    d: Dispenser,
    distance_mm: float,
    battery_v: float | None,
    at=None,
    device_fill_percent: float | None = None,
) -> tuple[float, Status]:
    """Save a reading, update the dispenser, and raise or resolve alerts.

    If the device sent its own fill % (the real Pico W does), it is used as is;
    otherwise it is worked out from the distance (the simulated dispensers).
    """
    at = at or utcnow()
    if device_fill_percent is not None:
        new_pct = round(device_fill_percent, 1)
    else:
        new_pct = reading_fill_percent(d, distance_mm)
    new_status = status_from_percent(new_pct)
    old_pct = d.last_fill_percent

    db.add(
        Reading(dispenser_id=d.id, distance_mm=distance_mm, fill_percent=new_pct, battery_v=battery_v, created_at=at)
    )

    # A big jump upward means someone refilled it.
    if old_pct is not None and new_pct - old_pct >= config.REFILL_JUMP_PERCENT:
        d.last_refill_at = at

    open_alerts = db.scalars(select(Alert).where(Alert.dispenser_id == d.id, Alert.resolved_at.is_(None))).all()
    open_levels = {a.level for a in open_alerts}

    if new_status == Status.FULL:
        # Back to full: close any open alerts.
        for a in open_alerts:
            a.resolved_at = at
    elif new_status == Status.EMPTY and Status.EMPTY not in open_levels:
        # Empty supersedes low, so close the low alert and raise an empty one.
        for a in open_alerts:
            a.resolved_at = at
        db.add(Alert(dispenser_id=d.id, level=Status.EMPTY, fill_percent=new_pct, created_at=at))
    elif new_status == Status.LOW and not open_levels:
        db.add(Alert(dispenser_id=d.id, level=Status.LOW, fill_percent=new_pct, created_at=at))
    elif new_status == Status.LOW and Status.EMPTY in open_levels:
        # Partly refilled from empty to low: swap the empty alert for a low one.
        for a in open_alerts:
            a.resolved_at = at
        db.add(Alert(dispenser_id=d.id, level=Status.LOW, fill_percent=new_pct, created_at=at))

    # Streaks: going empty breaks the streak; the next non-empty reading starts a new one.
    # The simulator keeps emptying and refilling the demo dispensers, which would
    # leave every demo streak at 0, so their new streaks are back-dated to their
    # stable made-up length (as at startup). The real box's streak is genuine.
    if new_status == Status.EMPTY:
        d.streak_started_at = None
    elif d.streak_started_at is None:
        d.streak_started_at = demo_streak_start(d.id, at) if config.SEED_DEMO_DATA and is_simulated(d) else at

    d.last_distance_mm = distance_mm
    d.last_fill_percent = new_pct
    d.last_reading_at = at
    db.commit()
    return new_pct, new_status


def sync_real_dispenser(db: Session) -> str:
    """Apply the real dispenser's settings from config (runs at every startup).

    Marks it as real, sets its calibration, and gives it the secret key from
    REAL_DEVICE_KEY. Returns a short message for the server log.
    """
    d = db.get(Dispenser, config.REAL_DISPENSER_ID)
    if d is None:
        return f"Real dispenser '{config.REAL_DISPENSER_ID}' not in the database; nothing to set up."
    d.is_real = True
    d.empty_distance_mm = config.REAL_EMPTY_DISTANCE_MM
    d.full_distance_mm = config.REAL_FULL_DISTANCE_MM
    if config.REAL_DEVICE_KEY:
        d.device_key = config.REAL_DEVICE_KEY
        key_note = "secret key from REAL_DEVICE_KEY"
    else:
        key_note = f"WARNING: REAL_DEVICE_KEY not set, still using '{d.device_key}'"
    db.commit()
    if config.REAL_LEVELS_MM:
        calibration = (
            f"counted by level ({config.REAL_CAPACITY} tampons, "
            f"{len(config.REAL_LEVELS_MM)} measured levels, column empty at {config.REAL_COLUMN_EMPTY_MM:g} mm)"
        )
    else:
        calibration = f"empty={d.empty_distance_mm:g} mm, full={d.full_distance_mm:g} mm"
    return f"Real dispenser '{d.id}': {calibration}, {key_note}."


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Straight-line distance between two points on Earth (haversine), in metres."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
