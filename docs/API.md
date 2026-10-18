# Code Red API

This is the contract between the backend and the frontend. If you change an
endpoint, update this file in the same commit and tell the other person.

- **Local base URL:** `http://localhost:8000`
- **Deployed base URL:** `https://code-red-api.onrender.com`
- **Interactive docs:** open `/docs` on either URL to try every endpoint in the browser.

All responses are JSON. All times are UTC in ISO 8601 format, ending in `Z`
(e.g. `2026-10-17T16:40:00Z`). In JavaScript, `new Date(value)` handles them.

---

## Status values

Every dispenser has exactly one `status`:

| Status | Meaning | Suggested pin color |
|---|---|---|
| `full` | above 50% | green |
| `low` | 15% to 50% | yellow/orange |
| `empty` | below 15% | red |
| `offline` | no reading in 2 minutes, or never reported | gray |

`fill_percent` and `units_left` are `null` until a dispenser has reported
at least once. For `offline` dispensers they show the **last known** value,
which may be out of date, so display it as "last seen" rather than current.

---

## The Dispenser object

Most endpoints return this shape:

```json
{
  "id": "klaus-atrium-pico-w",
  "building": {
    "id": 3,
    "name": "Klaus Advanced Computing Building",
    "lat": 33.7771,
    "lng": -84.3962
  },
  "floor": "1",
  "location_note": "Women's restroom off the atrium",
  "real": true,
  "status": "low",
  "fill_percent": 27.8,
  "units_left": 2,
  "last_reading_at": "2026-10-17T16:38:12Z",
  "last_refill_at": null,
  "streak_days": 12,
  "streak_started_at": "2026-10-05T14:02:00Z"
}
```

`streak_days` is the Snapchat-style streak: whole days since the dispenser was
last empty. It is `0` while the dispenser is empty (the streak is broken) and
starts again from 0 at the next non-empty reading. It is `null` if the dispenser
has never reported. Simulated dispensers start with a made-up streak of 1-60
days so the demo has history; the real dispenser's streak is always genuine.

`real` is `true` only for the physical dispenser (the Pico W); every other
dispenser is simulated. The frontend can use it for the "Live dispenser" badge
instead of hard-coding the ID.

Several dispensers can share a building (and so the same coordinates). On the
map, group them into one pin per building and list the dispensers by floor
when the pin is tapped.

---

## Student side

### `GET /dispensers`

Every dispenser. This is what the map loads. Poll it every 5 seconds to
keep pins up to date.

Optional query: `?status=full` (or `low`, `empty`, `offline`) to filter.

Returns: list of Dispenser objects.

### `POST /dispensers/nearest`

The closest dispensers that **still have products** (`full` or `low`),
nearest first. Empty and offline dispensers are left out.

Request body:

```json
{ "lat": 33.7745, "lng": -84.3965, "limit": 3 }
```

`limit` is optional (default 3, max 20).

Returns: list of Dispenser objects, each with an extra field
`"distance_m": 140` (straight-line metres, not walking distance).

> **Why POST?** The location goes in the request body instead of the URL,
> so it doesn't end up in server logs. The backend uses it for this one
> calculation and never stores it. Get the location in the browser with
> `navigator.geolocation.getCurrentPosition(...)`; this only works on
> `https://` sites or `localhost`.

### `GET /dispensers/{id}`

One dispenser. `404` if the ID doesn't exist.

### `GET /dispensers/{id}/history?hours=24`

Fill level over time, oldest first, for a chart.

```json
[
  { "distance_mm": 45.0, "fill_percent": 98.6, "created_at": "2026-10-17T15:40:00Z" },
  { "distance_mm": 300.0, "fill_percent": 27.8, "created_at": "2026-10-17T16:38:12Z" }
]
```

### `GET /buildings`

All buildings with coordinates, sorted by name.

---

## Staff side

There is no login yet. The frontend has a Student/Staff toggle that just
switches which screens are shown.

### `GET /staff/restock`

Empty dispensers only, longest empty first. Offline and low dispensers stay on
the map but do not appear in the urgent list. The website can instead sort the
same empty list by distance using the user's location in the browser; it does
not send or store that location. Returns Dispenser objects.

### `GET /staff/alerts`

Alerts raised when a dispenser drops to `low` or `empty`. An alert resolves
automatically when the dispenser is refilled.

Query options:

- `since=<time>`: only alerts created after this time
- `include_resolved=true`: include alerts that have been resolved

```json
[
  {
    "id": 12,
    "dispenser_id": "culc-1f",
    "building_name": "Clough Undergraduate Learning Commons",
    "floor": "1",
    "location_note": "Women's restroom by the main entrance",
    "level": "empty",
    "fill_percent": 5.6,
    "created_at": "2026-10-17T16:38:12Z",
    "resolved_at": null
  }
]
```

**Showing a banner for new alerts:** on page load, call `GET /staff/alerts`
and remember the newest `created_at`. Every 30 seconds, call
`GET /staff/alerts?since=<that time>`. Anything returned is new: show the
banner and update the remembered time. (URL-encode the time, e.g. with
`encodeURIComponent`.)

---

## Sensors

### `POST /readings`

Sent by each dispenser (or the simulator) every 5 seconds for the demo. The
frontend never calls this.

Header: `X-Device-Key: <the dispenser's secret>`

```json
{ "dispenser_id": "klaus-atrium-pico-w", "distance_mm": 300, "battery_v": 3.8 }
```

Returns `201` with `{ "dispenser_id": "klaus-atrium-pico-w", "fill_percent": 27.8, "status": "low" }`,
or `401` if the ID or key is wrong.

---

## Errors

Errors come back as `{ "detail": "..." }` with a matching HTTP status:
`401` wrong device key, `404` not found, `422` invalid request (the detail
explains which field).
