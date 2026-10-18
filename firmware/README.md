# Firmware

Code for the one real dispenser: **Raspberry Pi Pico W + CircuitPython + VL53L0X**.
Every other dispenser on the map is simulated (`simulator/fake_sensors.py`
leaves the real one alone).

| File | What it is |
|---|---|
| `code.py` | The program. Copy it to the Pico's `CIRCUITPY` drive. |
| `settings.toml.example` | Template for Wi-Fi, API URL, and device key. Copy it to the drive as `settings.toml`. |

## Wiring (VL53L0X → Pico W)

| VL53L0X | Pico W pin |
|---|---|
| VIN | 3V3 OUT (pin 36) |
| GND | any GND pin |
| SDA | GP14 (pin 19) |
| SCL | GP15 (pin 20) |

Mount the sensor in the **top lid, pointing straight down** the column.

## Setup

1. **Install CircuitPython** on the Pico W: hold BOOTSEL while plugging it in,
   then drag the Pico W `.uf2` from circuitpython.org onto the `RPI-RP2` drive.
   It reboots as a drive called `CIRCUITPY`.
2. **Install the libraries** with [circup](https://github.com/adafruit/circup):
   ```bash
   pip install circup
   circup install adafruit_vl53l0x adafruit_requests adafruit_connection_manager
   ```
   (Or copy those three from the Adafruit CircuitPython library bundle into
   `CIRCUITPY/lib/`.)
3. **Make a device key** (any long random string):
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"
   ```
   Put it in Render: **code-red-api → Environment → `REAL_DEVICE_KEY`**.
4. **Copy `settings.toml.example` to `CIRCUITPY/settings.toml`** and fill in
   your Wi-Fi and the same device key.
5. **Copy `code.py` to `CIRCUITPY/`.** It starts running immediately.

Watch what it's doing in the Thonny shell (or Mu, or
`screen /dev/tty.usbmodem* 115200` on a Mac).

## What it prints

Each line is the latest reading in inches and what the Pico thinks is in the box:

| Message | Meaning | Sent to the website? |
|---|---|---|
| `13 left (100% full)` … `7 left (54% full)` | Exact count | Yes |
| `LOW: 6 or fewer left, refill soon` | The column is empty; the sensor can only see the tray | Yes, as 23.1% (below 25%, "low", 3 left) |
| `LID OPEN: put the lid back on` | Nothing in range (the sensor reports 8190 mm) | No |
| `ERROR: … doesn't match any tampon level` | The reading settled between levels: lid or sensor shifted, or a tampon is tilted | No |

It sends whenever the count changes and every `REPORT_EVERY_SECONDS` otherwise.
While nothing is sent (lid open, error), the map shows the box as **offline**
after 2 minutes.

## Calibrating

The Pico counts tampons from levels measured on the real box (Oct 18 run,
13 tampons) and sends the fill % it works out (count ÷ 13) with each reading.
The backend saves that fill % as is; it doesn't recalculate it.

| Tampons left | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 or fewer |
|---|---|---|---|---|---|---|---|---|
| Reading (in) | 0.59 | 1.29 | 2.08 | 2.75 | 3.50 | 4.13 | 4.74 | 4.90 or more |
| Reading (mm) | 15 | 32.8 | 52.8 | 69.9 | 88.9 | 104.9 | 120.4 | 124.5 or more |

If the box, lid, or sensor position changes, measure again: set `CALIBRATE = 1`
in `settings.toml` (the Pico prints readings without sending them), note the
steady reading at each count, then update `BANDS` in `code.py` (inches, each
level ± about 0.2 in).

`REAL_LEVELS_MM` and `REAL_COLUMN_EMPTY_MM` on Render are only a fallback, used
if a reading arrives without a fill % (older firmware).

## Wi-Fi

eduroam's enterprise login doesn't work well on a Pico W. GTother works once the
Pico's MAC address (printed at startup) is registered with Georgia Tech; a phone
hotspot also works. The Pico W only supports **2.4 GHz**: on an iPhone hotspot,
turn on **Maximize Compatibility**.
