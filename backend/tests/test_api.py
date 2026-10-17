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


def test_real_dispenser_reading_uses_its_calibration(client):
    with next(app.dependency_overrides[get_db]()) as db:
        d = db.get(Dispenser, "near")
        d.is_real, d.empty_distance_mm, d.full_distance_mm = True, 155, 40
        db.commit()
    r = send(client, "near", 97.5, "k1").json()
    assert r["fill_percent"] == 50 and r["status"] == "low"
    out = client.get("/dispensers/near").json()
    assert out["real"] is True and out["units_left"] == 3  # 50% of (155-40)/18 ≈ 3
    assert client.get("/dispensers/far").json()["real"] is False


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
