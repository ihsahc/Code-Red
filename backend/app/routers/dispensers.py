"""Endpoints the map uses: list dispensers, one dispenser, history, nearest."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Building, Dispenser, Reading
from app.schemas import BuildingOut, DispenserOut, NearbyDispenserOut, NearestIn, ReadingOut
from app.services import dispenser_out, distance_m
from app.status import Status
from app.timeutil import to_utc, utcnow

router = APIRouter(tags=["Map"])


def _all_dispensers(db: Session) -> list[Dispenser]:
    return db.scalars(select(Dispenser).options(joinedload(Dispenser.building)).order_by(Dispenser.id)).all()


@router.get("/buildings", response_model=list[BuildingOut])
def list_buildings(db: Session = Depends(get_db)):
    return db.scalars(select(Building).order_by(Building.name)).all()


@router.get("/dispensers", response_model=list[DispenserOut])
def list_dispensers(
    status: Status | None = Query(default=None, description="Only return dispensers with this status"),
    db: Session = Depends(get_db),
):
    """Every dispenser with its location and current status. This is what the map loads."""
    now = utcnow()
    result = [dispenser_out(d, now) for d in _all_dispensers(db)]
    if status:
        result = [d for d in result if d.status == status]
    return result


@router.post("/dispensers/nearest", response_model=list[NearbyDispenserOut])
def nearest_dispensers(body: NearestIn, db: Session = Depends(get_db)):
    """Closest dispensers that still have products (full or low), nearest first.

    This is a POST so the user's location travels in the request body
    rather than the URL, where it could end up in server logs. The location
    is used for this calculation only and is never saved.
    """
    now = utcnow()
    candidates = []
    for d in _all_dispensers(db):
        out = dispenser_out(d, now)
        if out.status in (Status.FULL, Status.LOW):
            dist = distance_m(body.lat, body.lng, d.building.lat, d.building.lng)
            candidates.append(NearbyDispenserOut(**out.model_dump(), distance_m=round(dist)))
    candidates.sort(key=lambda c: c.distance_m)
    return candidates[: body.limit]


@router.get("/dispensers/{dispenser_id}", response_model=DispenserOut)
def get_dispenser(dispenser_id: str, db: Session = Depends(get_db)):
    d = db.get(Dispenser, dispenser_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Dispenser not found")
    return dispenser_out(d)


@router.get("/dispensers/{dispenser_id}/history", response_model=list[ReadingOut])
def dispenser_history(
    dispenser_id: str,
    hours: float = Query(default=24, gt=0, le=24 * 30),
    db: Session = Depends(get_db),
):
    """Fill level over time, oldest first, for a chart."""
    if db.get(Dispenser, dispenser_id) is None:
        raise HTTPException(status_code=404, detail="Dispenser not found")
    since = utcnow() - timedelta(hours=hours)
    rows = db.scalars(
        select(Reading)
        .where(Reading.dispenser_id == dispenser_id, Reading.created_at >= since)
        .order_by(Reading.created_at)
    ).all()
    return [
        ReadingOut(distance_mm=r.distance_mm, fill_percent=r.fill_percent, created_at=to_utc(r.created_at))
        for r in rows
    ]
