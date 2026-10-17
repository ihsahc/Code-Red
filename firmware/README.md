# Firmware

Raspberry Pi Pico W + CircuitPython + VL53L0X code for the dispenser. Not written yet.

## What the device needs to do

1. Every 5 seconds, take 10 distance readings from the VL53L0X and use the **median**.
2. Send it to the backend:

```
POST https://<your-app>.onrender.com/readings
Header: X-Device-Key: <this dispenser's key>
Body:   {"dispenser_id": "klaus-atrium-pico-w", "distance_mm": 300, "battery_v": 3.8}
```

3. Send the **raw distance**, not a percentage. The backend does the math, so
   calibration changes don't require reflashing the device.

## Wi-Fi

eduroam uses enterprise login, which is hard to set up on a Pico W. Check
whether Georgia Tech has a registered-device network you can use. A phone
hotspot works for the demo.

Keep the Wi-Fi password and device key in CircuitPython's `settings.toml`
(ignored by git).
