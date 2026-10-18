"""Code Red dispenser: Raspberry Pi Pico W + VL53L0X, CircuitPython.

Counts the tampons in the column and prints what it sees. Whenever the count
changes, and every few seconds anyway, it sends the fill percentage it worked
out, plus the settled sensor distance, to the backend (POST /readings). The
backend saves the Pico's fill % as is and works out the status from it.

Settings (Wi-Fi, API URL, device key) live in settings.toml on the CIRCUITPY
drive, not here. Set CALIBRATE = 1 there to print readings without sending.

Wiring (VL53L0X -> Pico W):
    VIN -> 3V3 OUT (pin 36)      GND -> any GND pin
    SDA -> GP14    (pin 19)      SCL -> GP15 (pin 20)
"""

import os
import time

import adafruit_connection_manager
import adafruit_requests
import adafruit_vl53l0x
import board
import busio
import wifi

# --- Settings (from settings.toml) -----------------------------------------
API_URL = (os.getenv("API_URL") or "https://code-red-api.onrender.com").rstrip("/")
DISPENSER_ID = os.getenv("DISPENSER_ID") or "klaus-atrium-pico-w"
DEVICE_KEY = os.getenv("DEVICE_KEY") or ""
# Keep this well under 2 minutes, or the map shows the box as "offline".
REPORT_EVERY_SECONDS = int(os.getenv("REPORT_EVERY_SECONDS") or 5)
# 1 = only print readings (for measuring), 0 = also send them to the website.
CALIBRATE = int(os.getenv("CALIBRATE") or 0)
REQUEST_TIMEOUT = 30  # seconds; the free Render server can take a while to wake up

# --- Sensor -----------------------------------------------------------------
i2c = busio.I2C(scl=board.GP15, sda=board.GP14)
tof = adafruit_vl53l0x.VL53L0X(i2c)
tof.measurement_timing_budget = 100000

TOTAL = 13
# Calibrated from the Oct 18 run (new setup).
# (tampons left, lowest OK reading, highest OK reading) in inches
# A reading that settles in a gap between bands = something is misaligned
BANDS = [
    (13, 0.40, 0.85),
    (12, 1.09, 1.49),
    (11, 1.88, 2.28),
    (10, 2.55, 2.95),
    (9, 3.30, 3.70),
    (8, 3.93, 4.33),
    (7, 4.54, 4.90),
]
TOO_CLOSE = 0.40  # closer than this: something is touching/blocking the sensor
LOW_ZONE = 4.90  # 4.90 to 6.00: column is empty, 6 or fewer left in the tray
LID_OPEN = 6.00  # farther than this: lid is off or the sensor isn't aimed into the column
# (322.44 in = 8190 mm is the sensor's "nothing in range" code)
STABLE_N = 3  # readings in a row that must agree (~1 second)
STABLE_SPREAD = 0.10  # how much they can differ and still count as "settled"


def read_inches():
    r = sorted(tof.range for _ in range(3))  # median of 3 quick readings
    return r[1] / 25.4


def match(d):
    if d < TOO_CLOSE:
        return "ERR"
    if d >= LOW_ZONE:
        return "LOW"
    for count, lo, hi in BANDS:
        if lo <= d <= hi:
            return count
    return "ERR"  # settled between bands = misaligned


# --- Wi-Fi and the website --------------------------------------------------
session = None


def connect():
    """Join Wi-Fi if needed and return an HTTP session."""
    global session
    if not wifi.radio.connected:
        ssid = os.getenv("CIRCUITPY_WIFI_SSID")
        print("Connecting to Wi-Fi:", ssid)
        wifi.radio.connect(ssid, os.getenv("CIRCUITPY_WIFI_PASSWORD"))
        session = None
    if session is None:
        print("Wi-Fi connected. IP:", wifi.radio.ipv4_address)
        pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
        ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
        session = adafruit_requests.Session(pool, ssl_context)
    return session


def fill_percent(count):
    """Fill % for a tampon count. "LOW" counts as the most that could be left."""
    if count == "LOW":
        count = TOTAL - len(BANDS)  # column empty: 6 or fewer left in the tray
    return round(count / TOTAL * 100, 1)


def send(distance_mm, pct):
    """POST one reading. Returns what the website now shows, or None if it failed."""
    global session
    try:
        response = connect().post(
            API_URL + "/readings",
            json={"dispenser_id": DISPENSER_ID, "distance_mm": distance_mm, "fill_percent": pct},
            headers={"X-Device-Key": DEVICE_KEY},
            timeout=REQUEST_TIMEOUT,
        )
        try:
            if response.status_code == 201:
                body = response.json()
                return "{}% {}".format(body["fill_percent"], body["status"])
            if response.status_code == 401:
                print("  Website said 401: DEVICE_KEY doesn't match REAL_DEVICE_KEY on Render.")
            else:
                print("  Website error", response.status_code, response.text[:120])
        finally:
            response.close()
    except Exception as e:  # Wi-Fi dropped, server asleep, ...: keep counting anyway
        print("  Couldn't send:", repr(e))
        session = None  # start a fresh connection next time
    return None


# --- Start up ---------------------------------------------------------------
print("MAC address:", ":".join(f"{b:02X}" for b in wifi.radio.mac_address))
if CALIBRATE:
    print("CALIBRATE = 1: printing readings only, not sending them.")
else:
    print("Reporting as", DISPENSER_ID, "to", API_URL)
    if not DEVICE_KEY:
        print("WARNING: DEVICE_KEY is empty in settings.toml; the website will reject readings.")
    try:
        connect()
    except Exception as e:
        print("Wi-Fi connection failed:", e, "(will keep trying)")

# --- Main loop ----------------------------------------------------------------
recent = []
status = "Starting up..."
good_mm = None  # latest settled reading that matched a tampon level, in mm
good_pct = None  # fill % for that reading
last_try = None  # when we last tried to send
last_try_status = None  # what the status was then

while True:
    d = read_inches()

    if d > LID_OPEN:
        # Can't be a reading from inside the box, so no need to wait for it to settle
        recent = []
        good_mm = None
        status = "LID OPEN: put the lid back on"
    else:
        recent.append(d)
        if len(recent) > STABLE_N:
            recent.pop(0)

        settled = len(recent) == STABLE_N and max(recent) - min(recent) <= STABLE_SPREAD
        if settled:
            avg = sum(recent) / STABLE_N
            result = match(avg)

            if result == "ERR":
                # Works at any fill level, including right after power-on
                good_mm = None
                status = (
                    f"ERROR: {avg:.2f} in doesn't match any tampon level. "
                    "Lid or sensor shifted, or a tampon is tilted. Fix and it will clear."
                )
            else:
                good_mm = round(avg * 25.4, 1)
                good_pct = fill_percent(result)
                if result == "LOW":
                    status = "LOW: 6 or fewer left, refill soon"
                else:
                    status = f"{result} left ({good_pct}% full)"

    print(f"{d:.2f} in -> {status}")

    # Send when the count changes, and every few seconds so the map doesn't
    # mark the box offline. Errors and an open lid are never sent.
    now = time.monotonic()
    due = last_try is None or status != last_try_status or now - last_try >= REPORT_EVERY_SECONDS
    if good_mm is not None and due and not CALIBRATE:
        last_try, last_try_status = now, status
        shown = send(good_mm, good_pct)
        if shown:
            print(f"  sent {good_pct}% ({good_mm} mm) -> website shows {shown}")

    time.sleep(0.05)
