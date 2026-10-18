"""All settings in one place.

Every value can be overridden with an environment variable of the same name,
so you can change them on Render without editing code.

The sensor numbers below are PLACEHOLDERS. Replace them once the real
dispenser is built and measured (see "Calibrating the sensor" in the README).
"""

import os


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _get_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes"}


def _get_floats(name: str, default: str) -> list[float]:
    """A comma-separated list of numbers, e.g. "15,32.8,52.8". Empty = []."""
    return [float(x) for x in os.getenv(name, default).replace(" ", "").split(",") if x]


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./dispensers.db")
    # Render hands out URLs starting with "postgres://" or "postgresql://".
    # Name the driver explicitly ("+psycopg", i.e. psycopg 3) so SQLAlchemy
    # doesn't guess, since its default driver has changed between versions.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix) :]
    return url


# --- Database -------------------------------------------------------------
DATABASE_URL = _database_url()

# Fill the database with demo buildings and dispensers when it is empty.
SEED_DEMO_DATA = _get_bool("SEED_DEMO_DATA", True)

# --- Sensor calibration (PLACEHOLDERS) ------------------------------------
# Distance from the VL53L0X to the top of a FULL stack, in millimetres.
FULL_DISTANCE_MM = _get_float("FULL_DISTANCE_MM", 50)
# Distance from the sensor to the floor of an EMPTY column, in millimetres.
EMPTY_DISTANCE_MM = _get_float("EMPTY_DISTANCE_MM", 400)
# Thickness of one wrapped tampon lying flat, in millimetres.
PRODUCT_THICKNESS_MM = _get_float("PRODUCT_THICKNESS_MM", 18)

# --- The one real dispenser -------------------------------------------------
# Every other dispenser is simulated and uses the defaults above. The real
# box is 15.5 cm tall, so it has its own calibration. Change these on Render
# (code-red-api -> Environment) once you've measured it; no code change needed.
REAL_DISPENSER_ID = os.getenv("REAL_DISPENSER_ID", "klaus-atrium-pico-w")

# The real box is counted level by level, from readings measured on it
# (Oct 18 calibration run, converted from inches). Its sensor reading doesn't
# grow evenly as tampons are taken, and once the column empties the sensor can
# only see the tray, so a straight line from "full" to "empty" gives wrong counts.
# How many tampons a full box holds.
REAL_CAPACITY = int(_get_float("REAL_CAPACITY", 13))
# Sensor reading in mm with a FULL box first, then one fewer tampon per step,
# down to the last level the sensor can see (here 13 left ... 7 left).
# Set it to "" on Render to go back to the straight-line formula below.
REAL_LEVELS_MM = _get_floats("REAL_LEVELS_MM", "15,32.8,52.8,69.9,88.9,104.9,120.4")
# At or beyond this reading the column is empty: the box reports
# REAL_CAPACITY - len(REAL_LEVELS_MM) left (here "6 or fewer", status "low").
REAL_COLUMN_EMPTY_MM = _get_float("REAL_COLUMN_EMPTY_MM", 124.5)

# Straight-line calibration, used only when REAL_LEVELS_MM is empty.
# Sensor reading with the box EMPTY (roughly the 155 mm box height).
REAL_EMPTY_DISTANCE_MM = _get_float("REAL_EMPTY_DISTANCE_MM", 155)
# Sensor reading with the box FULL.
REAL_FULL_DISTANCE_MM = _get_float("REAL_FULL_DISTANCE_MM", 40)
# Secret key the Pico W sends with each reading. Set it on Render only;
# never commit it. If unset, the box keeps its guessable demo key.
REAL_DEVICE_KEY = os.getenv("REAL_DEVICE_KEY", "").strip()

# --- Status rules ---------------------------------------------------------
# Above this fill percentage a dispenser counts as "full".
FULL_ABOVE_PERCENT = _get_float("FULL_ABOVE_PERCENT", 50)
# Below this fill percentage a dispenser counts as "empty".
EMPTY_BELOW_PERCENT = _get_float("EMPTY_BELOW_PERCENT", 15)
# A dispenser with no reading for this long counts as "offline".
OFFLINE_AFTER_MINUTES = _get_float("OFFLINE_AFTER_MINUTES", 2)
# A jump in fill this large between two readings is treated as a refill.
REFILL_JUMP_PERCENT = _get_float("REFILL_JUMP_PERCENT", 30)

# --- Web ------------------------------------------------------------------
# Which websites may call this API from a browser. "*" allows any site,
# which is fine for a hackathon. Later, set it to the frontend's URL, e.g.
# CORS_ORIGINS="https://code-red.onrender.com".
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
