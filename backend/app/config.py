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
FULL_DISTANCE_MM = _get_float("FULL_DISTANCE_MM", 40)
# Distance from the sensor to the floor of an EMPTY column, in millimetres.
EMPTY_DISTANCE_MM = _get_float("EMPTY_DISTANCE_MM", 400)
# Thickness of one wrapped tampon lying flat, in millimetres.
PRODUCT_THICKNESS_MM = _get_float("PRODUCT_THICKNESS_MM", 18)

# --- Status rules ---------------------------------------------------------
# Above this fill percentage a dispenser counts as "full".
FULL_ABOVE_PERCENT = _get_float("FULL_ABOVE_PERCENT", 60)
# Below this fill percentage a dispenser counts as "empty".
EMPTY_BELOW_PERCENT = _get_float("EMPTY_BELOW_PERCENT", 15)
# A dispenser with no reading for this long counts as "offline".
OFFLINE_AFTER_MINUTES = _get_float("OFFLINE_AFTER_MINUTES", 15)
# A jump in fill this large between two readings is treated as a refill.
REFILL_JUMP_PERCENT = _get_float("REFILL_JUMP_PERCENT", 15)

# --- Web ------------------------------------------------------------------
# Which websites may call this API from a browser. "*" allows any site,
# which is fine for a hackathon. Later, set it to the frontend's URL, e.g.
# CORS_ORIGINS="https://code-red.onrender.com".
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
