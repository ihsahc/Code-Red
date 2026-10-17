"""Endpoints for the staff view: the restock list and alerts.

There is no login yet: the frontend has a Student/Staff toggle. If you add a
password later, it only needs to be checked in this file.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Alert, Dispenser
from app.schemas import AlertOut, DispenserOut
from app.services import alert_out, dispenser_out
from app.status import Status
from app.timeutil import to_naive_utc, utcnow

router = APIRouter(prefix="/staff", tags=["Staff"])


@router.get("/restock", response_model=list[DispenserOut])
def restock_list(db: Session = Depends(get_db)):
    """Empty dispensers only, with the longest-empty shown first."""
    now = utcnow()
    dispensers = db.scalars(select(Dispenser).options(joinedload(Dispenser.building))).all()
    empty = [o for o in (dispenser_out(d, now) for d in dispensers) if o.status == Status.EMPTY]
    open_alerts = db.scalars(select(Alert).where(Alert.resolved_at.is_(None), Alert.level == Status.EMPTY)).all()
    empty_since = {a.dispenser_id: a.created_at for a in open_alerts}
    empty.sort(key=lambda o: empty_since.get(o.id, now))
    return empty


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    since: datetime | None = Query(
        default=None,
        description="Only alerts raised after this time. Poll with the newest created_at you've seen "
        "to get new ones for the banner.",
    ),
    include_resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """Low/empty alerts, newest first. Open alerts only, unless include_resolved=true."""
    q = select(Alert).options(joinedload(Alert.dispenser).joinedload(Dispenser.building))
    if not include_resolved:
        q = q.where(Alert.resolved_at.is_(None))
    if since is not None:
        q = q.where(Alert.created_at > to_naive_utc(since))
    return [alert_out(a) for a in db.scalars(q.order_by(Alert.created_at.desc())).all()]
