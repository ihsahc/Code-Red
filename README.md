# Code-Red

A phone-friendly website that shows Georgia Tech students live fill levels of
tampon dispensers across campus. It directs students to the nearest stocked
dispenser (15%+) and shows facilities staff which empty dispenser needs a
refill first.

Each dispenser has a sensor that measures how full it is, and the map shows
which dispensers are **full**, **running low**, or **empty**, and points you
to the closest one that still has products.

Built for **Hack Like W@CC** (theme: Back to 2016, track: Health & Accessibility).

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

A time-of-flight sensor at the top of the product column measures the
distance down to the top of the stack. As products are taken, the distance
grows. The backend converts that into a fill percentage and a status, and
raises an alert for staff when a dispenser runs low or empty.

## Repo layout

```
backend/     FastAPI server, database, status logic, tests
index.html, app.js, style.css, config.js, data.js  The phone-friendly website
simulator/   Fake sensors for demos without hardware
firmware/    Pico W / CircuitPython notes for the real dispenser
docs/        API.md: the contract between backend and frontend
```

## Running the backend locally

Needs Python 3.11 or newer.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** to see and try every endpoint. The first
run creates `dispensers.db` and fills it with demo buildings and dispensers.

To start over with fresh demo data: `python -m app.seed --reset`

## Running the simulator

With the backend running, in a second terminal (from the repo root):

```bash
python simulator/fake_sensors.py --interval 5 --busy
```

Every dispenser starts reporting. Levels drop, alerts appear, and empty
dispensers occasionally get refilled. Use `--url https://<your-app>.onrender.com`
to drive the deployed version, and `--skip p264079` to leave one dispenser
silent so it shows as offline.

## Tests

```bash
cd backend
pytest
```

## Calibrating the sensor

The **real dispenser** (the Pico W) is already calibrated: the Pico counts it
level by level from readings measured on the box and sends its own fill % to
the backend (`BANDS` in `firmware/code.py`; how to redo it is in
`firmware/README.md`).

The values below are for the **simulated** dispensers and are placeholders.
Update them in `backend/app/config.py` (or set them as environment variables
on Render):

| Setting | How to measure | Placeholder |
|---|---|---|
| `FULL_DISTANCE_MM` | Sensor reading with the column completely full | 50 |
| `EMPTY_DISTANCE_MM` | Sensor reading with the column completely empty | 400 |
| `PRODUCT_THICKNESS_MM` | Thickness of one wrapped tampon lying flat | 18 |

Keep the sensor at least 3 to 4 cm above a full stack: the VL53L0X is
unreliable very close up. Also update the same numbers at the top of
`simulator/fake_sensors.py`.

Status rules (also in `config.py`): **full** above 50%, **low** 15–50%,
**empty** below 15%, **offline** after 2 minutes with no reading. A fill jump
of 30 percentage points or more marks a refill.

## Running the website

Start the API first, then serve the repository root (do not double-click
`index.html`; browsers restrict some features when it is opened as a file):

```bash
python -m http.server 8080
```

Open `http://localhost:8080`. The default API URL in `config.js` is
`http://localhost:8000`. When the API is unavailable, the site labels and uses
its local demo fallback. Before deploying the static site to GitHub Pages,
replace `API_BASE_URL` in `config.js` with the HTTPS Render URL.

## Deploying to Render (free)

1. Push this repo to GitHub.
2. On [render.com](https://render.com), choose **New → Blueprint** and pick this repo.
   Render reads `render.yaml` and creates the API and a free Postgres database.
3. Once it's live, open `https://<your-app>.onrender.com/docs` to check it.
4. Put that URL in `docs/API.md` and in the frontend's config.

Things to know about the free tier:

- The app **sleeps after 15 minutes without traffic** and takes about a
  minute to wake up. Sensors or the simulator reporting every few minutes
  keep it awake. Open the site a few minutes before presenting anyway.
- The free Postgres database **expires 30 days after it's created**, so
  create it close to the event.

## How we work

- Don't commit straight to `main`. Make a branch (`backend/alerts`,
  `frontend/map`), push it, and open a pull request.
- Pull `main` before starting new work: `git pull origin main`.
- Format Python before committing: `ruff format . && ruff check --fix .`
- If you change an endpoint, update `docs/API.md` in the same pull request.
