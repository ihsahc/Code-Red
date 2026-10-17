"""Demo data: a few campus buildings and dispensers in a mix of states.

Runs automatically on startup when the database is empty (SEED_DEMO_DATA=true).
To wipe and re-seed locally:   python -m app.seed --reset

The coordinates are APPROXIMATE building locations, good enough for a demo
map. Check them on a real map before relying on them.

Demo device keys follow the pattern "demo-<dispenser id>" so the simulator
can report for every dispenser. Give real devices random keys instead.
"""

import argparse
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Building, Dispenser
from app.services import record_reading
from app.timeutil import utcnow

BUILDINGS = [
    # name, lat, lng  (approximate)
    ("John Lewis Student Center", 33.7740, -84.3988),
    ("Clough Undergraduate Learning Commons", 33.7746, -84.3964),
    ("Klaus Advanced Computing Building", 33.7771, -84.3962),
    ("Price Gilbert Library", 33.7743, -84.3957),
    ("Campus Recreation Center", 33.7756, -84.4038),
    ("Howey Physics Building", 33.7775, -84.3988),
    ("Scheller College of Business", 33.7764, -84.3876),
    ("West Village", 33.7796, -84.4048),
]

DISPENSERS = [
    # id, building, floor, location note, starting distance in mm (None = offline)
    ("stuc-1f", "John Lewis Student Center", "1", "Women's restroom near the food court", 70),
    ("stuc-2f", "John Lewis Student Center", "2", "Women's restroom by the ballrooms", 260),
    ("culc-1f", "Clough Undergraduate Learning Commons", "1", "Women's restroom by the main entrance", 380),
    ("culc-3f", "Clough Undergraduate Learning Commons", "3", "Women's restroom near the study rooms", 90),
    ("klaus-1f", "Klaus Advanced Computing Building", "1", "Women's restroom off the atrium", 300),
    ("library-2f", "Price Gilbert Library", "2", "Women's restroom by the elevators", 55),
    ("crc-1f", "Campus Recreation Center", "1", "Women's locker room", None),
    ("howey-1f", "Howey Physics Building", "1", "Women's restroom by the lecture halls", 120),
    ("scheller-2f", "Scheller College of Business", "2", "Women's restroom near the cafe", 240),
    ("wv-1f", "West Village", "1", "Women's restroom by the dining hall", 60),
]


def seed(db: Session) -> None:
    buildings = {}
    for name, lat, lng in BUILDINGS:
        b = Building(name=name, lat=lat, lng=lng)
        db.add(b)
        buildings[name] = b
    db.flush()

    now = utcnow()
    for dispenser_id, building, floor, note, distance in DISPENSERS:
        d = Dispenser(
            id=dispenser_id,
            building_id=buildings[building].id,
            floor=floor,
            location_note=note,
            device_key=f"demo-{dispenser_id}",
        )
        db.add(d)
        db.flush()
        d.building = buildings[building]
        if distance is None:
            # Last heard from three hours ago, so it shows as offline.
            record_reading(db, d, 150, None, at=now - timedelta(hours=3))
        else:
            # Start every dispenser full an hour ago, then move to its current level,
            # so alerts and history look realistic.
            record_reading(db, d, 45, 3.9, at=now - timedelta(hours=1))
            record_reading(db, d, distance, 3.8, at=now - timedelta(minutes=2))
    db.commit()


def seed_if_empty() -> bool:
    with SessionLocal() as db:
        if db.scalar(select(Building).limit(1)) is not None:
            return False
        seed(db)
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load demo data")
    parser.add_argument("--reset", action="store_true", help="Delete all data first")
    args = parser.parse_args()
    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Seeded demo data." if seed_if_empty() else "Database already has data; use --reset to start over.")
