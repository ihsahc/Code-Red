# Code-Red
Code-Red is a website (made for phones) that shows how full the tampon dispensers around Georgia Tech are in real time. Students can find the closest dispenser that still has products, and facilities staff can see which empty dispensers to refill first.

Each dispenser has a sensor that measures how full it is, and the map shows which dispensers are full, lower, or running low, and points you to the closest one that still has products.

## How it works

```
 Dispenser                      Backend (FastAPI)                Website
 ┌──────────────┐  every 5 sec  ┌──────────────────────┐  JSON   ┌───────────────┐
 │ Pico W +     │ ────────────▶ │ distance → fill %    │ ◀────── │ Student: map, │
 │ VL53L0X      │  POST         │ → full/low/empty     │  GET    │ nearest       │
 │ distance     │  /readings    │ alerts for staff     │         │ Staff: restock│
 └──────────────┘               └──────────────────────┘         │ list, alerts  │
                                                                 └───────────────┘
```

A time-of-flight sensor at the top of the product column measures the distance down to the top of the stack. As products are taken, the distance grows. The backend converts that into a fill percentage and a status, and raises an alert for staff when a dispenser runs low or empty.

## Repo layout

```
backend/     FastAPI server, database, status logic, tests
index.html, app.js, style.css, config.js, data.js  The phone-friendly website
simulator/   Fake sensors for demos without hardware
firmware/    Pico W / CircuitPython notes for the real dispenser
docs/        API.md: the contract between backend and frontend
```

Link to active application: [https://code-red-yrtq.onrender.com/](url)

## Running the simulator

With the backend running, in a second terminal (from the repo root):

```bash
python simulator/fake_sensors.py --interval 5 --busy
```
## Tests

```bash
cd backend
pytest
```

## Calibrating the sensor

The sensor should already be calibrated. Put the products into the physical dispenser and for each possible fill level do multiple trials. Using these distances calibrate the approximate changes in distance for each tampon you take out and use this to calculate percentages.

## Deploying to Render (free)

1. Push this repo to GitHub.
2. Go to the Render Website and create a blueprint for the repo
3. Make sure your website is consistently active otherwise it will stop working under the free model. Running the simulation should take care of this problem as it updates every 30 seconds
