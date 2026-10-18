"""Endpoint the dispenser sensors (or the simulator) report to."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dispenser
from app.schemas import ReadingAccepted, ReadingIn
from app.services import record_reading

router = APIRouter(tags=["Sensors"])


@router.post("/readings", response_model=ReadingAccepted, status_code=201)
def post_reading(
    body: ReadingIn,
    x_device_key: str = Header(description="The dispenser's secret key"),
    db: Session = Depends(get_db),
):
    """Record one sensor reading. Send the raw distance, plus fill_percent if the device
    works it out itself (the real Pico W does); otherwise the server works it out."""
    d = db.get(Dispenser, body.dispenser_id)
    # Same error for "no such dispenser" and "wrong key", so the response
    # doesn't reveal which dispenser IDs exist.
    if d is None or not secrets.compare_digest(d.device_key, x_device_key):
        raise HTTPException(status_code=401, detail="Unknown dispenser or wrong device key")
    pct, status = record_reading(db, d, body.distance_mm, body.battery_v, device_fill_percent=body.fill_percent)
    return ReadingAccepted(dispenser_id=d.id, fill_percent=pct, status=status)
