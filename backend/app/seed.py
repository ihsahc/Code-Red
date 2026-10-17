"""Demo data: 19 campus dispensers in a mix of states.

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

DISPENSERS = [
    # id, building, floor, location note, lat, lng, starting distance (None = offline)
    ("p264591", "Clough Undergraduate Learning Commons", "Floor 1", "Women's restroom", 33.774868, -84.396400, 92),
    ("p264520", "Gilbert Memorial Library", "Floor 1", "Women's restroom", 33.774426, -84.395790, 148),
    ("klaus-atrium-pico-w", "Klaus Advanced Computing Building", "Atrium", "Women's restroom in the Klaus atrium", 33.777524, -84.396128, 208),
    ("p279898", "Stamps Health Services", "Floor 1", "Women's restroom", 33.774773, -84.402885, 260),
    ("p473312", "Kendeda Building", "Floor 2", "Women's restroom", 33.778774, -84.399574, 323),
    ("p264141", "Skiles", "Floor 1", "Women's restroom", 33.773582, -84.395950, 358),
    ("p279888", "Van Leer Building", "Floor 1", "Women's restroom", 33.775948, -84.397141, 383),
    ("p264081", "College of Computing", "Floor 1", "Women's restroom", 33.777363, -84.397354, 400),
    ("p264568", "Ferst Center for the Arts", "Floor 1", "Women's restroom", 33.775181, -84.399338, 68),
    ("p451379", "Instructional Center", "Floor 1", "Women's restroom", 33.775505, -84.401314, 295),
    ("p264079", "Tech Tower", "Floor 1", "Women's restroom", 33.772457, -84.394730, None),
    ("p261362", "Lyman Hall", "Floor 1", "Women's restroom", 33.772926, -84.394096, 337),
    ("p377482", "McCamish Pavilion", "Floor 1", "Women's restroom", 33.780731, -84.392822, 372),
    ("p279901", "West Village Dining Commons", "Floor 1", "Women's restroom", 33.779331, -84.404793, 134),
    ("p279193", "Howey School of Physics", "Floor 1", "Women's restroom", 33.777431, -84.398552, 239),
    ("p264602", "Marcus Nanotechnology Building", "Floor 1", "Women's restroom", 33.778912, -84.398628, 50),
    ("p347966", "North Avenue Dining", "Floor 1", "Women's restroom", 33.770973, -84.391121, 278),
    ("p264950", "Smithgall Student Services Building", "Floor 1", "Women's restroom", 33.774384, -84.399590, 351),
    ("p264600", "TSRB", "Floor 1", "Women's restroom", 33.777115, -84.390083, 190),
]


def seed(db: Session) -> None:
    buildings = {}
    for _, name, _, _, lat, lng, _ in DISPENSERS:
        if name not in buildings:
            buildings[name] = Building(name=name, lat=lat, lng=lng)
            db.add(buildings[name])
    db.flush()

    now = utcnow()
    for dispenser_id, building, floor, note, _, _, distance in DISPENSERS:
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
            record_reading(db, d, 50, 3.9, at=now - timedelta(hours=1))
            record_reading(db, d, distance, 3.8, at=now - timedelta(seconds=30))
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
