"""Code Red dispenser: Raspberry Pi Pico W + VL53L0X, CircuitPython.

Every few seconds this measures the distance from the sensor (mounted at the
top of the box, pointing down) to the top of the tampon stack, and sends it
to the backend. The backend turns the distance into a fill percentage, so
calibration changes never need this file to be re-flashed.

Settings (Wi-Fi, API URL, device key) live in settings.toml, not here.
Set CALIBRATE = 1 in settings.toml to just print distances for measuring.

Wiring (VL53L0X -> Pico W):
    VIN -> 3V3 OUT (pin 36)      GND -> GND (pin 38)
    SDA -> GP4     (pin 6)       SCL -> GP5 (pin 7)

The LED on the Pico W blinks:
    once      reading sent successfully
    twice     the sensor didn't see anything (lid open? sensor blocked?)
    3 times   couldn't send (Wi-Fi, server, or wrong key: check the serial output)
"""

import os
import time

import adafruit_connection_manager
import adafruit_requests
import adafruit_vl53l0x
import board
import busio
import digitalio
import microcontroller
import wifi

# --- Settings (from settings.toml) ---------------------------------------
API_URL = (os.getenv("API_URL") or "https://code-red-api.onrender.com").rstrip("/")
DISPENSER_ID = os.getenv("DISPENSER_ID") or "klaus-atrium-pico-w"
DEVICE_KEY = os.getenv("DEVICE_KEY") or ""
REPORT_EVERY_SECONDS = int(os.getenv("REPORT_EVERY_SECONDS") or 5)
CALIBRATE = int(os.getenv("CALIBRATE") or 0)

SAMPLES = 10  # readings per report; we send the median
MAX_VALID_MM = 1200  # the sensor reports ~8190 when it sees nothing at all
REQUEST_TIMEOUT = 30  # seconds; the free Render server can take a while to wake up
RESET_AFTER_FAILURES = 12  # restart the board if this many reports in a row fail


# --- Helpers ----------------------------------------------------------------


def blink(led, times=1, on=0.08, off=0.12):
    for _ in range(times):
        led.value = True
        time.sleep(on)
        led.value = False
        time.sleep(off)


def median(values):
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def read_distance(sensor, samples=SAMPLES):
    """Median of several readings in mm, or None if the sensor sees nothing useful."""
    valid = []
    for _ in range(samples):
        mm = sensor.range
        if 0 < mm < MAX_VALID_MM:
            valid.append(mm)
    # Need at least half the readings to agree that something is there.
    if len(valid) < samples // 2:
        return None
    return median(valid)


def setup_led():
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    return led


def setup_sensor(led):
    """Start the VL53L0X, retrying (and blinking) until it answers."""
    while True:
        try:
            i2c = busio.I2C(board.GP5, board.GP4)  # SCL, SDA
            sensor = adafruit_vl53l0x.VL53L0X(i2c)
            # A longer timing budget gives steadier readings (0.2 s each).
            sensor.measurement_timing_budget = 200000
            print("Sensor ready.")
            return sensor
        except (ValueError, RuntimeError, OSError) as e:
            print("Can't find the VL53L0X:", e)
            print("Check wiring: SDA->GP4, SCL->GP5, VIN->3V3, GND->GND. Retrying in 5 s.")
            blink(led, 3, 0.05, 0.1)
            time.sleep(5)


def connect_wifi():
    if wifi.radio.connected:
        return
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    print("Connecting to Wi-Fi:", ssid)
    wifi.radio.connect(ssid, os.getenv("CIRCUITPY_WIFI_PASSWORD"))
    print("Connected, IP:", wifi.radio.ipv4_address)


def make_session():
    pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
    return adafruit_requests.Session(pool, ssl_context)


def send_reading(session, distance_mm):
    """POST one reading. Returns True if the backend accepted it."""
    response = session.post(
        API_URL + "/readings",
        json={"dispenser_id": DISPENSER_ID, "distance_mm": distance_mm},
        headers={"X-Device-Key": DEVICE_KEY},
        timeout=REQUEST_TIMEOUT,
    )
    try:
        if response.status_code == 201:
            body = response.json()
            print("Sent {} mm -> {}% ({})".format(distance_mm, body["fill_percent"], body["status"]))
            return True
        if response.status_code == 401:
            print("Rejected (401): DISPENSER_ID or DEVICE_KEY doesn't match the backend.")
        else:
            print("Backend error", response.status_code, response.text[:200])
        return False
    finally:
        response.close()


# --- Modes --------------------------------------------------------------------


def calibrate(sensor, led):
    """Print distances twice a second, without sending anything.

    Use it to measure: empty the box and note the reading (REAL_EMPTY_DISTANCE_MM),
    then fill it and note the reading (REAL_FULL_DISTANCE_MM).
    """
    print("CALIBRATE mode: printing distances only. Set CALIBRATE = 0 to start reporting.")
    while True:
        mm = read_distance(sensor)
        print("distance:", "nothing detected" if mm is None else f"{mm} mm")
        led.value = not led.value
        time.sleep(0.5)


def report_forever(sensor, led):
    if not DEVICE_KEY:
        print("WARNING: DEVICE_KEY is empty in settings.toml; the backend will reject readings.")
    session = None
    failures = 0
    while True:
        started = time.monotonic()
        ok = False
        skipped = False
        try:
            mm = read_distance(sensor)
            if mm is None:
                # Nothing to measure (lid open, sensor blocked?). Don't send a bogus
                # value; the map will show "offline" if this goes on for a while.
                print("No valid reading this round; skipping.")
                skipped = True
            else:
                connect_wifi()
                if session is None:
                    session = make_session()
                ok = send_reading(session, mm)
        except Exception as e:  # keep running no matter what goes wrong
            print("Error:", repr(e))
            session = None  # rebuild the connection next time

        if ok:
            failures = 0
            blink(led, 1)
        elif skipped:
            blink(led, 2, 0.05, 0.1)  # sensor problem, not a network one: no restart
        else:
            failures += 1
            blink(led, 3, 0.05, 0.1)
            if failures >= RESET_AFTER_FAILURES:
                print("Too many failures in a row; restarting the board.")
                time.sleep(1)
                microcontroller.reset()

        # Keep a steady rhythm no matter how long the request took.
        elapsed = time.monotonic() - started
        time.sleep(max(0, REPORT_EVERY_SECONDS - elapsed))


def main():
    led = setup_led()
    sensor = setup_sensor(led)
    if CALIBRATE:
        calibrate(sensor, led)
    else:
        print("Reporting as", DISPENSER_ID, "to", API_URL, "every", REPORT_EVERY_SECONDS, "s")
        report_forever(sensor, led)


main()
