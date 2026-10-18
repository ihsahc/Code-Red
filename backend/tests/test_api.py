"""Run from the backend folder with:  pytest"""

import os
from datetime import timedelta

# Use a fresh in-memory database for tests and skip the demo data.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEED_DEMO_DATA"] = "false"

import pytest  # noqa: E402
from app import database  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Building, Dispenser  # noqa: E402
from app.status import Status, current_status, fill_percent, status_from_percent  # noqa: E402
from app.timeutil import utcnow  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

FULL_MM, EMPTY_MM, LOW_MM = 50, 400, 225


@pytest.fixture
def client():
    engine = database.create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Session = database.sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with Session() as db:
        db.add(Building(id=1, name="Klaus", lat=33.7771, lng=-84.3962))
        db.add(Building(id=2, name="CRC", lat=33.7756, lng=-84.4038))
        db.add(Dispenser(id="near", building_id=1, floor="1", location_note="", device_key="k1"))
        db.add(Dispenser(id="far", building_id=2, floor="1", location_note="", device_key="k2"))
        db.commit()

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def send(client, dispenser_id, distance_mm, key):
    return client.post(
        "/readings", json={"dispenser_id": dispenser_id, "distance_mm": distance_mm}, headers={"X-Device-Key": key}
    )


# --- Fill math -------------------------------------------------------------


def test_fill_percent_endpoints_and_clamping():
    assert fill_percent(FULL_MM) == 100
    assert fill_percent(EMPTY_MM) == 0
    assert fill_percent(225) == 50
    assert fill_percent(10) == 100  # closer than "full" still counts as 100
    assert fill_percent(900) == 0  # farther than "empty" still counts as 0


def test_status_thresholds():
    assert status_from_percent(51) == Status.FULL
    assert status_from_percent(50) == Status.LOW
    assert status_from_percent(15) == Status.LOW
    assert status_from_percent(14.9) == Status.EMPTY


def test_offline_after_silence():
    now = utcnow()
    assert current_status(90, now - timedelta(minutes=1), now) == Status.FULL
    assert current_status(90, now - timedelta(minutes=3), now) == Status.OFFLINE
    assert current_status(None, None, now) == Status.OFFLINE


# --- Readings --------------------------------------------------------------


def test_reading_requires_correct_key(client):
    assert send(client, "near", 100, "wrong").status_code == 401
    assert send(client, "nope", 100, "k1").status_code == 401
    assert client.post("/readings", json={"dispenser_id": "near", "distance_mm": 100}).status_code == 422


def test_reading_updates_dispenser(client):
    r = send(client, "near", 225, "k1")
    assert r.status_code == 201
    assert r.json() == {"dispenser_id": "near", "fill_percent": 50.0, "status": "low"}
    d = client.get("/dispensers/near").json()
    assert d["status"] == "low" and d["fill_percent"] == 50.0 and d["units_left"] == 10


def test_reading_uses_device_fill_percent(client):
    # 225 mm would work out to 50%, but the device's own fill % wins.
    r = client.post(
        "/readings",
        json={"dispenser_id": "near", "distance_mm": 225, "fill_percent": 84.6},
        headers={"X-Device-Key": "k1"},
    )
    assert r.json() == {"dispenser_id": "near", "fill_percent": 84.6, "status": "full"}
    assert client.get("/dispensers/near").json()["fill_percent"] == 84.6
    assert client.get("/dispensers/near/history").json()[-1]["fill_percent"] == 84.6
    bad = {"dispenser_id": "near", "distance_mm": 225, "fill_percent": 101}
    assert client.post("/readings", json=bad, headers={"X-Device-Key": "k1"}).status_code == 422


def test_never_reported_shows_offline(client):
    assert client.get("/dispensers/far").json()["status"] == "offline"


# --- Alerts ----------------------------------------------------------------


def test_alert_lifecycle(client):
    send(client, "near", FULL_MM, "k1")
    assert client.get("/staff/alerts").json() == []

    send(client, "near", LOW_MM, "k1")
    send(client, "near", LOW_MM + 10, "k1")  # still low: no duplicate alert
    alerts = client.get("/staff/alerts").json()
    assert [a["level"] for a in alerts] == ["low"]

    send(client, "near", EMPTY_MM, "k1")  # empty replaces low
    assert [a["level"] for a in client.get("/staff/alerts").json()] == ["empty"]

    send(client, "near", FULL_MM, "k1")  # refilled: all resolved
    assert client.get("/staff/alerts").json() == []
    assert len(client.get("/staff/alerts?include_resolved=true").json()) == 2
    assert client.get("/dispensers/near").json()["last_refill_at"] is not None


def test_alerts_since_filter(client):
    send(client, "near", LOW_MM, "k1")
    newest = client.get("/staff/alerts").json()[0]["created_at"]
    assert client.get("/staff/alerts", params={"since": newest}).json() == []


# --- Map and staff views ---------------------------------------------------


def test_restock_list_has_only_empty_dispensers(client):
    send(client, "near", LOW_MM, "k1")
    assert client.get("/staff/restock").json() == []
    send(client, "near", EMPTY_MM, "k1")
    assert [d["id"] for d in client.get("/staff/restock").json()] == ["near"]


def test_nearest_skips_empty_and_offline(client):
    send(client, "near", EMPTY_MM, "k1")
    send(client, "far", FULL_MM, "k2")
    klaus = {"lat": 33.7771, "lng": -84.3962}
    result = client.post("/dispensers/nearest", json=klaus).json()
    assert [d["id"] for d in result] == ["far"]
    assert result[0]["distance_m"] > 0


def test_status_filter(client):
    send(client, "near", FULL_MM, "k1")
    assert [d["id"] for d in client.get("/dispensers?status=full").json()] == ["near"]


# --- The real dispenser ------------------------------------------------------


def make_db():
    engine = database.create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine, database.sessionmaker(bind=engine, expire_on_commit=False)


def test_fill_percent_with_own_calibration():
    # The real box: 155 mm when empty, 40 mm when full.
    assert fill_percent(155, 155, 40) == 0
    assert fill_percent(40, 155, 40) == 100
    assert fill_percent(97.5, 155, 40) == 50
    # Simulated dispensers still use the defaults.
    assert fill_percent(225) == 50


def test_sync_real_dispenser_sets_calibration_and_key(monkeypatch):
    from app import config
    from app.services import sync_real_dispenser

    monkeypatch.setattr(config, "REAL_DISPENSER_ID", "pico")
    monkeypatch.setattr(config, "REAL_EMPTY_DISTANCE_MM", 155)
    monkeypatch.setattr(config, "REAL_FULL_DISTANCE_MM", 40)
    monkeypatch.setattr(config, "REAL_DEVICE_KEY", "s3cret")
    _, Session = make_db()
    with Session() as db:
        db.add(Building(id=1, name="Klaus", lat=33.7771, lng=-84.3962))
        db.add(Dispenser(id="pico", building_id=1, floor="1", location_note="", device_key="demo-pico"))
        db.add(Dispenser(id="fake", building_id=1, floor="1", location_note="", device_key="demo-fake"))
        db.commit()
        assert "secret key" in sync_real_dispenser(db)
        pico, fake = db.get(Dispenser, "pico"), db.get(Dispenser, "fake")
        assert pico.is_real and pico.device_key == "s3cret"
        assert (pico.empty_distance_mm, pico.full_distance_mm) == (155, 40)
        assert not fake.is_real and fake.empty_distance_mm is None


def test_sync_warns_without_key(monkeypatch):
    from app import config
    from app.services import sync_real_dispenser

    monkeypatch.setattr(config, "REAL_DISPENSER_ID", "pico")
    monkeypatch.setattr(config, "REAL_DEVICE_KEY", "")
    _, Session = make_db()
    with Session() as db:
        db.add(Building(id=1, name="Klaus", lat=33.7771, lng=-84.3962))
        db.add(Dispenser(id="pico", building_id=1, floor="1", location_note="", device_key="demo-pico"))
        db.commit()
        assert "WARNING" in sync_real_dispenser(db)
        assert db.get(Dispenser, "pico").device_key == "demo-pico"


def test_real_dispenser_straight_line_fallback(client, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "REAL_LEVELS_MM", [])  # REAL_LEVELS_MM="" on Render
    with next(app.dependency_overrides[get_db]()) as db:
        d = db.get(Dispenser, "near")
        d.is_real, d.empty_distance_mm, d.full_distance_mm = True, 155, 40
        db.commit()
    r = send(client, "near", 97.5, "k1").json()
    assert r["fill_percent"] == 50 and r["status"] == "low"
    out = client.get("/dispensers/near").json()
    assert out["real"] is True and out["units_left"] == 3  # 50% of (155-40)/18 ≈ 3
    assert client.get("/dispensers/far").json()["real"] is False


# Every steady reading from the Oct 18 calibration run (inches, as logged on the
# Pico), lowest and highest, with how many tampons were in the box.
CALIBRATION_RUN_IN = [
    (13, 0.55, 0.70),
    (12, 1.29, 1.37),
    (11, 2.00, 2.12),
    (10, 2.71, 2.79),
    (9, 3.46, 3.54),
    (8, 4.09, 4.17),
    (7, 4.68, 4.76),
    (6, 5.19, 5.23),  # column just emptied
    (6, 5.00, 5.11),  # "6 or fewer": the sensor only sees the tray now
]


def test_units_from_levels_matches_calibration_run():
    from app import config
    from app.status import units_from_levels

    for expected, low_in, high_in in CALIBRATION_RUN_IN:
        for inches in (low_in, high_in):
            got = units_from_levels(
                inches * 25.4, config.REAL_LEVELS_MM, config.REAL_COLUMN_EMPTY_MM, config.REAL_CAPACITY
            )
            assert got == expected, f"{inches} in should be {expected} left, got {got}"


def test_real_dispenser_counts_by_level(client):
    with next(app.dependency_overrides[get_db]()) as db:
        db.get(Dispenser, "near").is_real = True
        db.commit()

    def reading(mm):
        r = send(client, "near", mm, "k1").json()
        out = client.get("/dispensers/near").json()
        return r["fill_percent"], r["status"], out["units_left"]

    assert reading(15.0) == (100.0, "full", 13)
    assert reading(88.9) == (69.2, "full", 9)
    assert reading(120.4) == (53.8, "full", 7)
    assert client.get("/staff/alerts").json() == []
    # Column empty: "6 or fewer", which raises a low alert for staff.
    assert reading(127.8) == (46.2, "low", 6)
    assert [a["level"] for a in client.get("/staff/alerts").json()] == ["low"]
    # Refilled: back to 13, alert resolved, refill recorded.
    assert reading(15.0) == (100.0, "full", 13)
    assert client.get("/staff/alerts").json() == []
    assert client.get("/dispensers/near").json()["last_refill_at"] is not None
    # Simulated dispensers still use the straight line.
    assert send(client, "far", LOW_MM, "k2").json()["fill_percent"] == 50


def test_add_missing_columns_upgrades_old_database():
    from app.database import add_missing_columns
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy import text

    engine = database.create_engine("sqlite://", poolclass=StaticPool)
    with engine.begin() as conn:  # a dispensers table from before the new columns existed
        conn.execute(
            text(
                "CREATE TABLE dispensers (id VARCHAR(64) PRIMARY KEY, building_id INTEGER, floor VARCHAR(20),"
                " location_note VARCHAR(200), device_key VARCHAR(64))"
            )
        )
        conn.execute(text("INSERT INTO dispensers VALUES ('x', 1, '1', '', 'k')"))
    added = add_missing_columns(engine)
    assert "dispensers.is_real" in added and "dispensers.empty_distance_mm" in added
    cols = {c["name"] for c in sa_inspect(engine).get_columns("dispensers")}
    assert {"is_real", "empty_distance_mm", "full_distance_mm", "last_fill_percent"} <= cols
    assert add_missing_columns(engine) == []  # running again changes nothing
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id FROM dispensers")).scalar() == "x"  # data kept


# --- Demo data sync ----------------------------------------------------------


def test_sync_demo_data_adds_updates_and_removes(monkeypatch):
    from app import seed as seed_mod
    from app.models import Alert, Reading

    monkeypatch.setattr(config_module(), "REAL_DISPENSER_ID", "pico")
    rows = [
        ("a", "Klaus", "Floor 1", "Women's restroom", 33.7771, -84.3962, 225),
        ("b", "Klaus", "Floor 2", "Women's restroom", 33.7771, -84.3962, 400),
        ("pico", "Klaus", "Atrium", "Real box", 33.7771, -84.3962, 100),
    ]
    monkeypatch.setattr(seed_mod, "DISPENSERS", rows)
    _, Session = make_db()
    with Session() as db:
        assert seed_mod.sync_demo_data(db) == {"added": 3, "removed": 0, "total": 3}
        assert db.get(Dispenser, "pico").last_reading_at is None  # real box: no fake history
        level_a = db.get(Dispenser, "a").last_fill_percent

        # An old dispenser that's no longer listed, with readings and an alert.
        db.add(Building(name="Old", lat=1, lng=1))
        db.flush()
        old_b = db.scalar(select_building("Old"))
        db.add(Dispenser(id="old", building_id=old_b.id, floor="1", location_note="", device_key="k"))
        db.flush()
        from app.services import record_reading

        record_reading(db, db.get(Dispenser, "old"), 400, None)

        # Rename a floor and drop "b" from the list; run again.
        monkeypatch.setattr(
            seed_mod, "DISPENSERS", [("a", "Klaus", "Ground", "Renamed", 33.7771, -84.3962, 225), rows[2]]
        )
        assert seed_mod.sync_demo_data(db) == {"added": 0, "removed": 2, "total": 2}
        a = db.get(Dispenser, "a")
        assert (a.floor, a.location_note, a.last_fill_percent) == ("Ground", "Renamed", level_a)  # readings kept
        assert db.get(Dispenser, "b") is None and db.get(Dispenser, "old") is None
        assert db.scalar(select_building("Old")) is None  # empty building removed
        assert not db.query(Reading).filter_by(dispenser_id="old").count()
        assert not db.query(Alert).filter_by(dispenser_id="old").count()

        # Running again with no changes does nothing.
        assert seed_mod.sync_demo_data(db) == {"added": 0, "removed": 0, "total": 2}


def test_sync_never_removes_the_real_dispenser(monkeypatch):
    from app import seed as seed_mod

    monkeypatch.setattr(seed_mod, "DISPENSERS", [("a", "Klaus", "1", "", 33.7, -84.3, 225)])
    _, Session = make_db()
    with Session() as db:
        db.add(Building(id=9, name="Elsewhere", lat=1, lng=1))
        db.add(Dispenser(id="pico", building_id=9, floor="1", location_note="", device_key="k", is_real=True))
        db.commit()
        assert seed_mod.sync_demo_data(db)["removed"] == 0
        assert db.get(Dispenser, "pico") is not None


def test_backend_seed_matches_website_fallback_data():
    """seed.py (live data) and data.js (website fallback) must list the same dispensers."""
    import pathlib
    import re

    from app.seed import DISPENSERS

    data_js = (pathlib.Path(__file__).resolve().parents[2] / "data.js").read_text()
    pattern = r'id:\s*"([^"]+)",\s*building:\s*"([^"]+)",\s*floor:\s*"([^"]+)",\s*lat:\s*([-\d.]+),\s*lng:\s*([-\d.]+)'
    website = {m[0]: (m[1], m[2], float(m[3]), float(m[4])) for m in re.findall(pattern, data_js)}
    backend = {r[0]: (r[1], r[2], r[4], r[5]) for r in DISPENSERS}
    assert set(website) == set(backend), (
        f"Only on website: {set(website) - set(backend)}; only in backend: {set(backend) - set(website)}"
    )
    for dispenser_id, (building, floor, lat, lng) in backend.items():
        w = website[dispenser_id]
        assert (w[0], w[1]) == (building, floor), (
            f"{dispenser_id}: website has {w[:2]}, backend has {(building, floor)}"
        )
        assert abs(w[2] - lat) < 1e-6 and abs(w[3] - lng) < 1e-6, f"{dispenser_id}: coordinates differ"


def config_module():
    from app import config

    return config


def select_building(name):
    from sqlalchemy import select

    return select(Building).where(Building.name == name)


# --- Streaks -------------------------------------------------------------------


def test_streak_breaks_when_empty_and_restarts_on_refill(client):
    assert client.get("/dispensers/near").json()["streak_days"] is None  # never reported
    send(client, "near", FULL_MM, "k1")
    d = client.get("/dispensers/near").json()
    assert d["streak_days"] == 0 and d["streak_started_at"] is not None  # streak begins

    # Pretend the streak started 9 days ago.
    with next(app.dependency_overrides[get_db]()) as db:
        db.get(Dispenser, "near").streak_started_at = utcnow() - timedelta(days=9, hours=1)
        db.commit()
    send(client, "near", LOW_MM, "k1")  # running low keeps the streak
    assert client.get("/dispensers/near").json()["streak_days"] == 9

    send(client, "near", EMPTY_MM, "k1")  # empty breaks it
    d = client.get("/dispensers/near").json()
    assert d["streak_days"] == 0 and d["streak_started_at"] is None

    send(client, "near", FULL_MM, "k1")  # refilled: a new streak starts from now
    d = client.get("/dispensers/near").json()
    assert d["streak_days"] == 0 and d["streak_started_at"] is not None


def test_demo_streaks_are_stable_and_skip_real_and_empty(monkeypatch):
    from app import seed as seed_mod

    monkeypatch.setattr(config_module(), "REAL_DISPENSER_ID", "pico")
    rows = [
        ("stocked", "Klaus", "1", "", 33.7, -84.3, 100),
        ("empty", "Klaus", "2", "", 33.7, -84.3, 400),
        ("pico", "Klaus", "3", "", 33.7, -84.3, 100),
    ]
    monkeypatch.setattr(seed_mod, "DISPENSERS", rows)
    _, Session = make_db()
    with Session() as db:
        seed_mod.sync_demo_data(db)
        now = utcnow()
        stocked = db.get(Dispenser, "stocked")
        days = (now - stocked.streak_started_at).days
        assert days == seed_mod.demo_streak_days("stocked") and 1 <= days <= 31
        assert db.get(Dispenser, "empty").streak_started_at is None
        assert db.get(Dispenser, "pico").streak_started_at is None  # real box: no fake history

        first = stocked.streak_started_at
        seed_mod.sync_demo_data(db)  # restart: existing streaks untouched
        assert db.get(Dispenser, "stocked").streak_started_at == first


def test_old_long_demo_streaks_are_rerolled_into_range(monkeypatch):
    from app import seed as seed_mod

    monkeypatch.setattr(config_module(), "REAL_DISPENSER_ID", "pico")
    monkeypatch.setattr(seed_mod, "DISPENSERS", [("a", "Klaus", "1", "", 33.7, -84.3, 100)])
    _, Session = make_db()
    with Session() as db:
        seed_mod.sync_demo_data(db)
        db.get(Dispenser, "a").streak_started_at = utcnow() - timedelta(days=55)  # from the old 1-60 range
        db.commit()
        seed_mod.sync_demo_data(db)
        days = (utcnow() - db.get(Dispenser, "a").streak_started_at).days
        assert 1 <= days <= 31
    assert all(1 <= seed_mod.demo_streak_days(f"id{i}") <= 31 for i in range(500))
