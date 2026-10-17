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
| GND | GND (pin 38) |
| SDA | GP4 (pin 6) |
| SCL | GP5 (pin 7) |

Mount the sensor at the **top of the box, pointing straight down** at the stack.
Keep at least 3–4 cm between the sensor and a full stack; the VL53L0X is
unreliable closer than that.

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

Watch what it's doing in a serial console (Mu editor, or
`screen /dev/tty.usbmodem* 115200` on a Mac).

## Calibrating

1. Set `CALIBRATE = 1` in `settings.toml`. The Pico prints distances instead of sending them.
2. Empty the box and note the distance → `REAL_EMPTY_DISTANCE_MM` on Render.
3. Fill the box and note the distance → `REAL_FULL_DISTANCE_MM` on Render.
4. Set `CALIBRATE = 0` again.

Render restarts the API when you change an environment variable, and the new
calibration applies to the next reading. The placeholders are 155 mm (empty,
the box height) and 40 mm (full).

## LED

| Blinks | Meaning |
|---|---|
| 1 | Reading sent |
| 2 | Sensor saw nothing (lid open? blocked?) |
| 3 | Couldn't send: Wi-Fi, server, or wrong key (check the serial output) |

After 12 failed sends in a row, the board restarts itself.

## Wi-Fi

eduroam's enterprise login doesn't work well on a Pico W. Use a phone hotspot
or a network without a login page. The Pico W only supports **2.4 GHz**: on an
iPhone hotspot, turn on **Maximize Compatibility**.
