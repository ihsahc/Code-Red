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

# --- Certificates ---------------------------------------------------------------
# The website (*.onrender.com) uses a certificate from Let's Encrypt's new
# "Root YR" (intermediates YR1/YR2). The Pico's built-in certificate list can't
# verify that newer chain (OSError MBEDTLS_ERR_X509_FATAL_ERROR), so we tell it
# to trust these two Let's Encrypt roots directly. This replaces the built-in list
# for this connection. Root YR is valid until 2045; ISRG Root X1 until 2035.
TRUSTED_ROOTS = """
-----BEGIN CERTIFICATE-----
MIIFKTCCAxGgAwIBAgIRAOxGNJNgz0sP+KmC2Tqpyj0wDQYJKoZIhvcNAQELBQAw
LjELMAkGA1UEBhMCVVMxDTALBgNVBAoTBElTUkcxEDAOBgNVBAMTB1Jvb3QgWVIw
HhcNMjUwOTAzMDAwMDAwWhcNNDUwOTAyMjM1OTU5WjAuMQswCQYDVQQGEwJVUzEN
MAsGA1UEChMESVNSRzEQMA4GA1UEAxMHUm9vdCBZUjCCAiIwDQYJKoZIhvcNAQEB
BQADggIPADCCAgoCggIBANvGJnN78CTJdWL3+eGfsLN5TrNBJs+VH9hRXqRbwxu9
sGNiB0BD1fcOxbSUQCJIM1xE13Db+5Cw1w0s0EBYsvuIP/6joF0w8cuImbgR1OGg
YbSQ4OpzI+DG8SGuTlcE873OCS+kh3srlo6vl43M5OJg4Aeo1sfHp6kTJDoIiFBN
JAY+OKfX/FUvYKuhjT+no49lmqmupSBI5PkBQiqrEGtWU5uxU/cQWHGu8jSjFBzn
ZqvbNPLMXMLFxCb3WTfrJBXXjqvWG+v4bjzxjjeAtOlU7qarRDvNOyAuQYLln904
M+faKx8hnLCpJ15ZqaEgcNlY+9MMWcC5yvL2A2j3l9+2buggZX+dOE91zYmIdawT
vSZuVvlbRrAlLxIB6pwMBjneXCjYQ8+3BCCjssbSNpZU3hTcBDdhfAlEDlYr6pEa
tnMdmDT5BqnKC92bd0EhM1fbLHioLccLCuievT8ZkPhZrq7Mii7gNXAcUEAR8+lz
Yal+9zTg7C5DALyVOeG/CqfRAMn1KSHCR0NSA6P8tn/mGRlnCct5rtVCLnVySVpU
6H1qGg3DgTOuskf8eahTMiYbI5ezPJmO5ertalskQ1utp74+eDy92PI4ftHKTbq9
IWhH4YZKh3WnJEIt+oQvlYZbY8tpEroKrFB6PFGzrJIDRyts4HqvuH52RFj2zv/B
AgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNVHRMBAf8EBTADAQH/MB0GA1Ud
DgQWBBTe51tg0CJtQCh9Pw0B/qS1UrRRlDANBgkqhkiG9w0BAQsFAAOCAgEAWHnf
713Bdkq7t5yN2dNIgQakUb94X9WuyhMEHHkgx4oDpSUlnG0w4g94MoqaEUE31ZjR
LU7L5LD1g9ujFHTQu8AD215AHMVQFbm6j8hQxdXHAzDajFNQnOlDJrLjzIx176oy
AjvUtejZx2NNmdb5fd0WGVGsCdoAJ3N8ozo7ajE8t6vfxStZb4BQ9WYJGHUDrv2N
i5tJF6CNiPnlzs3BUfECRbE4JSk+jvy8+VoGiFE8qsH/j78x2fjgQhAQFV7P7Zxy
dBTZ1wEkNpZNW2qnaK1SKBLa+xf6E06YRIq5uaI+HWH8SY1y5VbRgzq40EKg3yxP
06fz+uYAUIFJoLNfhwRCc3Q6pQVuMX3yAjHAes4gk4moGcLQ5p7HAh39yeylZc1J
41sx/jKwLIkPE6Rr1Nf4pxdsxf9SA4yOEiAkDgq04DVxn8hgYFdUtBCuiuVC2heA
EiqVEa+8QZjuw8Gj0EbHXcRd1nInvGqRS1o9Is7YBdQN57X1AYveGBNNqjICSb7c
awuw1EawTDrs13VUlJVEsbQ0/O/1aaV73mCdOQ8azqL2KTv1Ewu1xbquE2S+kdQU
To9TUwat3wUA6cwXh1EfpS/3fJ0aGah5hdpRyoCLDlsSn8tkrjMfFFX0viC+GxHc
sI1ANRYvqSFC2X1VRZfDg+wD6E21BccmifG4yWc=
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
"""

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
        ssl_context.load_verify_locations(cadata=TRUSTED_ROOTS)
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
        if "MBEDTLS" in repr(e):
            print("  (Certificate check failed. On GTother? Make sure the Pico's MAC address")
            print("   printed at startup is registered with Georgia Tech, or try a phone hotspot.)")
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
