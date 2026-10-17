# Frontend

The phone-friendly website: a campus map for students and a restock view for staff.

**Everything the backend provides is described in [`docs/API.md`](../docs/API.md).**
With the backend running locally, you can also try every endpoint at
http://localhost:8000/docs.

## What the backend gives you

- `GET /dispensers`: every dispenser with coordinates and status, for the map pins
- `POST /dispensers/nearest`: closest dispensers that still have products
- `GET /staff/restock`: what needs refilling, most urgent first
- `GET /staff/alerts`: low/empty alerts, for the staff banner

## Getting started without waiting for the backend

Run the backend locally (see the main README) and start the simulator so the
data changes while you build:

```bash
python simulator/fake_sensors.py --interval 5 --busy
```

## Tips

- Keep the API base URL in one place (a config file or constant) so switching
  from `http://localhost:8000` to the Render URL is a one-line change.
- Location (`navigator.geolocation`) only works on `https://` or `localhost`.
  When testing on a phone, use the deployed site.
