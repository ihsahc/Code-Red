"""Demo data: 71 dispensers across 19 campus buildings (one per floor), in a mix of states.

On every startup (with SEED_DEMO_DATA=true) the database is updated to match
the DISPENSERS list below, so to add, remove or move a dispenser on the live
site, edit the list and push. Keep it in sync with data.js (the website's
offline fallback); tests/test_api.py checks that the two match.
To wipe everything and start over locally:   python -m app.seed --reset

The coordinates are APPROXIMATE building locations, good enough for a demo
map. Check them on a real map before relying on them.

Demo device keys follow the pattern "demo-<dispenser id>" so the simulator
can report for every dispenser. Give real devices random keys instead.
"""

import argparse
import hashlib
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import config
from app.database import Base, SessionLocal, engine
from app.models import Alert, Building, Dispenser, Reading
from app.services import record_reading
from app.timeutil import utcnow

DISPENSERS = [
    # id, building, floor, location note, lat, lng, starting distance in mm (None = offline)
    # Several floors share a building (same lat/lng). Floor counts are approximate placeholders.
    # distance_mm = 400 - fill% * 3.5   (so 0% = 400 mm, 100% = 50 mm)
    ("p264591", "Clough Undergraduate Learning Commons", "Floor 1", "Women's restroom", 33.774868, -84.396400, 92),
    ("p264591-f2", "Clough Undergraduate Learning Commons", "Floor 2", "Women's restroom", 33.774868, -84.396400, 183),
    ("p264591-f3", "Clough Undergraduate Learning Commons", "Floor 3", "Women's restroom", 33.774868, -84.396400, 278),
    ("p264591-f4", "Clough Undergraduate Learning Commons", "Floor 4", "Women's restroom", 33.774868, -84.396400, 358),
    ("p264591-f5", "Clough Undergraduate Learning Commons", "Floor 5", "Women's restroom", 33.774868, -84.396400, 141),
    ("p264520", "Gilbert Memorial Library", "Floor 1", "Women's restroom", 33.774426, -84.395790, 148),
    ("p264520-f2", "Gilbert Memorial Library", "Floor 2", "Women's restroom", 33.774426, -84.395790, 232),
    ("p264520-f3", "Gilbert Memorial Library", "Floor 3", "Women's restroom", 33.774426, -84.395790, 330),
    ("p264520-f4", "Gilbert Memorial Library", "Floor 4", "Women's restroom", 33.774426, -84.395790, 368),
    ("p264520-f5", "Gilbert Memorial Library", "Floor 5", "Women's restroom", 33.774426, -84.395790, 208),
    ("klaus-atrium-pico-w", "Klaus Advanced Computing Building", "Atrium", "Women's restroom in the Klaus atrium", 33.777524, -84.396128, 208),
    ("klaus-f2", "Klaus Advanced Computing Building", "Floor 2", "Women's restroom", 33.777524, -84.396128, 292),
    ("klaus-f3", "Klaus Advanced Computing Building", "Floor 3", "Women's restroom", 33.777524, -84.396128, 351),
    ("klaus-f4", "Klaus Advanced Computing Building", "Floor 4", "Women's restroom", 33.777524, -84.396128, 400),
    ("klaus-f5", "Klaus Advanced Computing Building", "Floor 5", "Women's restroom", 33.777524, -84.396128, 169),
    ("p279898", "Stamps Health Services", "Floor 1", "Women's restroom", 33.774773, -84.402885, 260),
    ("p279898-f2", "Stamps Health Services", "Floor 2", "Women's restroom", 33.774773, -84.402885, 337),
    ("p473312-f1", "Kendeda Building", "Floor 1", "Women's restroom", 33.778774, -84.399574, 368),
    ("p473312", "Kendeda Building", "Floor 2", "Women's restroom", 33.778774, -84.399574, 323),
    ("p473312-f3", "Kendeda Building", "Floor 3", "Women's restroom", 33.778774, -84.399574, 400),
    ("p473312-f4", "Kendeda Building", "Floor 4", "Women's restroom", 33.778774, -84.399574, 358),
    ("p264141", "Skiles", "Floor 1", "Women's restroom", 33.773582, -84.395950, 358),
    ("p264141-f2", "Skiles", "Floor 2", "Women's restroom", 33.773582, -84.395950, 379),
    ("p264141-f3", "Skiles", "Floor 3", "Women's restroom", 33.773582, -84.395950, 400),
    ("p264141-f4", "Skiles", "Floor 4", "Women's restroom", 33.773582, -84.395950, 390),
    ("p279888", "Van Leer Building", "Floor 1", "Women's restroom", 33.775948, -84.397141, 382),
    ("p279888-f2", "Van Leer Building", "Floor 2", "Women's restroom", 33.775948, -84.397141, 400),
    ("p279888-f3", "Van Leer Building", "Floor 3", "Women's restroom", 33.775948, -84.397141, 351),
    ("p279888-f4", "Van Leer Building", "Floor 4", "Women's restroom", 33.775948, -84.397141, 393),
    ("p279888-f5", "Van Leer Building", "Floor 5", "Women's restroom", 33.775948, -84.397141, 368),
    ("p264081", "College of Computing", "Floor 1", "Women's restroom", 33.777363, -84.397354, 400),
    ("p264081-f2", "College of Computing", "Floor 2", "Women's restroom", 33.777363, -84.397354, 267),
    ("p264081-f3", "College of Computing", "Floor 3", "Women's restroom", 33.777363, -84.397354, 400),
    ("p264081-f4", "College of Computing", "Floor 4", "Women's restroom", 33.777363, -84.397354, 306),
    ("p264568", "Ferst Center for the Arts", "Floor 1", "Women's restroom", 33.775181, -84.399338, 68),
    ("p264568-f2", "Ferst Center for the Arts", "Floor 2", "Women's restroom", 33.775181, -84.399338, 116),
    ("p264568-f3", "Ferst Center for the Arts", "Floor 3", "Women's restroom", 33.775181, -84.399338, 190),
    ("p451379", "Instructional Center", "Floor 1", "Women's restroom", 33.775505, -84.401314, 295),
    ("p451379-f2", "Instructional Center", "Floor 2", "Women's restroom", 33.775505, -84.401314, 218),
    ("p451379-f3", "Instructional Center", "Floor 3", "Women's restroom", 33.775505, -84.401314, 340),
    ("p451379-f4", "Instructional Center", "Floor 4", "Women's restroom", 33.775505, -84.401314, 246),
    ("p264079", "Tech Tower", "Floor 1", "Women's restroom", 33.772457, -84.394730, None),
    ("p264079-f2", "Tech Tower", "Floor 2", "Women's restroom", 33.772457, -84.394730, 197),
    ("p264079-f3", "Tech Tower", "Floor 3", "Women's restroom", 33.772457, -84.394730, 326),
    ("p264079-f4", "Tech Tower", "Floor 4", "Women's restroom", 33.772457, -84.394730, 376),
    ("p261362", "Lyman Hall", "Floor 1", "Women's restroom", 33.772926, -84.394096, 337),
    ("p261362-f2", "Lyman Hall", "Floor 2", "Women's restroom", 33.772926, -84.394096, 284),
    ("p261362-f3", "Lyman Hall", "Floor 3", "Women's restroom", 33.772926, -84.394096, 386),
    ("p377482", "McCamish Pavilion", "Floor 1", "Women's restroom", 33.780731, -84.392822, 372),
    ("p377482-f2", "McCamish Pavilion", "Floor 2", "Women's restroom", 33.780731, -84.392822, 400),
    ("p377482-f3", "McCamish Pavilion", "Floor 3", "Women's restroom", 33.780731, -84.392822, 362),
    ("p279901", "West Village Dining Commons", "Floor 1", "Women's restroom", 33.779331, -84.404793, 134),
    ("p279901-f2", "West Village Dining Commons", "Floor 2", "Women's restroom", 33.779331, -84.404793, 218),
    ("p279193", "Howey School of Physics", "Floor 1", "Women's restroom", 33.777431, -84.398552, 239),
    ("p279193-f2", "Howey School of Physics", "Floor 2", "Women's restroom", 33.777431, -84.398552, 155),
    ("p279193-f3", "Howey School of Physics", "Floor 3", "Women's restroom", 33.777431, -84.398552, 312),
    ("p279193-f4", "Howey School of Physics", "Floor 4", "Women's restroom", 33.777431, -84.398552, 368),
    ("p264602", "Marcus Nanotechnology Building", "Floor 1", "Women's restroom", 33.778912, -84.398628, 50),
    ("p264602-f2", "Marcus Nanotechnology Building", "Floor 2", "Women's restroom", 33.778912, -84.398628, 102),
    ("p264602-f3", "Marcus Nanotechnology Building", "Floor 3", "Women's restroom", 33.778912, -84.398628, 260),
    ("p264602-f4", "Marcus Nanotechnology Building", "Floor 4", "Women's restroom", 33.778912, -84.398628, 344),
    ("p347966", "North Avenue Dining", "Floor 1", "Women's restroom", 33.770973, -84.391121, 278),
    ("p347966-f2", "North Avenue Dining", "Floor 2", "Women's restroom", 33.770973, -84.391121, 365),
    ("p264950", "Smithgall Student Services Building", "Floor 1", "Women's restroom", 33.774384, -84.399590, 351),
    ("p264950-f2", "Smithgall Student Services Building", "Floor 2", "Women's restroom", 33.774384, -84.399590, 298),
    ("p264950-f3", "Smithgall Student Services Building", "Floor 3", "Women's restroom", 33.774384, -84.399590, 256),
    ("p264600", "TSRB", "Floor 1", "Women's restroom", 33.777115, -84.390083, 190),
    ("p264600-f2", "TSRB", "Floor 2", "Women's restroom", 33.777115, -84.390083, 246),
    ("p264600-f3", "TSRB", "Floor 3", "Women's restroom", 33.777115, -84.390083, 358),
    ("p264600-f4", "TSRB", "Floor 4", "Women's restroom", 33.777115, -84.390083, 400),
    ("p264600-f5", "TSRB", "Floor 5", "Women's restroom", 33.777115, -84.390083, 292),
]


def _add_starting_readings(db: Session, d: Dispenser, distance: float | None) -> None:
    if d.id == config.REAL_DISPENSER_ID:
        # The real box gets no fake history: it shows as offline until
        # the Pico W sends its first reading.
        return
    now = utcnow()
    if distance is None:
        # Last heard from three hours ago, so it shows as offline.
        record_reading(db, d, 150, None, at=now - timedelta(hours=3))
    else:
        # Start full an hour ago, then move to its current level,
        # so alerts and history look realistic.
        record_reading(db, d, 50, 3.9, at=now - timedelta(hours=1))
        record_reading(db, d, distance, 3.8, at=now - timedelta(seconds=30))


def demo_streak_days(dispenser_id: str) -> int:
    """A made-up but stable streak length (1-60 days) for a simulated dispenser.

    Real streaks only grow one day per day, so a fresh demo would show 0 everywhere.
    Hashing the ID gives each simulated dispenser its own believable history that
    stays the same across restarts.
    """
    return int(hashlib.sha256(dispenser_id.encode()).hexdigest(), 16) % 60 + 1


def _give_demo_streak(d: Dispenser, new: bool) -> None:
    """Back-date a simulated dispenser's streak so the staff view has history to show.

    Only for simulated dispensers that aren't empty and don't have a streak from an
    earlier run (new ones always get one). The real box's streak is always genuine.
    """
    if d.is_real or d.id == config.REAL_DISPENSER_ID:
        return
    if d.last_fill_percent is None or d.last_fill_percent < config.EMPTY_BELOW_PERCENT:
        return
    if new or d.streak_started_at is None:
        d.streak_started_at = utcnow() - timedelta(days=demo_streak_days(d.id), hours=3)


def sync_demo_data(db: Session) -> dict[str, int]:
    """Make the database's buildings and dispensers match DISPENSERS above.

    Runs on every startup, so editing the list and pushing is all it takes:
    - dispensers in the list but not the database are added, with starting levels
    - dispensers in both keep their readings; name, floor and location are updated
    - dispensers no longer in the list are removed with their readings and alerts
      (never the real one)
    """
    wanted_ids = {row[0] for row in DISPENSERS}

    buildings = {b.name: b for b in db.scalars(select(Building))}
    for _, name, _, _, lat, lng, _ in DISPENSERS:
        if name in buildings:
            buildings[name].lat, buildings[name].lng = lat, lng
        else:
            buildings[name] = Building(name=name, lat=lat, lng=lng)
            db.add(buildings[name])
    db.flush()

    existing = {d.id: d for d in db.scalars(select(Dispenser))}
    removed = 0
    for dispenser_id, d in existing.items():
        if dispenser_id not in wanted_ids and not d.is_real:
            db.execute(delete(Alert).where(Alert.dispenser_id == dispenser_id))
            db.execute(delete(Reading).where(Reading.dispenser_id == dispenser_id))
            db.delete(d)
            removed += 1
    db.flush()

    added = 0
    for dispenser_id, building, floor, note, _, _, distance in DISPENSERS:
        d = existing.get(dispenser_id)
        if d is not None:
            d.building_id, d.floor, d.location_note = buildings[building].id, floor, note
            _give_demo_streak(d, new=False)
            continue
        d = Dispenser(
            id=dispenser_id,
            building_id=buildings[building].id,
            floor=floor,
            location_note=note,
            device_key=f"demo-{dispenser_id}",
        )
        db.add(d)
        db.flush()
        _add_starting_readings(db, d, distance)
        _give_demo_streak(d, new=True)
        added += 1
    db.flush()

    # Remove buildings that no longer have any dispensers.
    in_use = set(db.scalars(select(Dispenser.building_id)))
    for b in buildings.values():
        if b.id not in in_use:
            db.delete(b)
    db.commit()
    return {"added": added, "removed": removed, "total": len(wanted_ids)}


def seed(db: Session) -> None:
    """Fill an empty database (kept for --reset and older callers)."""
    sync_demo_data(db)


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