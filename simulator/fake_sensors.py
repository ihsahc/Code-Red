"""Pretend to be every dispenser, so you can demo without hardware.

Each round, every dispenser sends a reading to the API exactly like a real
Pico W would. Products get taken at random, so levels drift down, alerts
appear, and the occasional dispenser gets refilled.

Usage (backend must be running):
    python simulator/fake_sensors.py                      # local backend
    python simulator/fake_sensors.py --url https://<your-app>.onrender.com
    python simulator/fake_sensors.py --interval 5 --busy  # fast, for a live demo
    python simulator/fake_sensors.py --skip p264079        # leave one offline

Needs only the "httpx" package (pip install httpx).
Uses the demo device keys from backend/app/seed.py ("demo-<dispenser id>").
"""

import argparse
import random
import statistics
import time

import httpx

# Keep these in sync with backend/app/config.py (placeholders for now).
FULL_MM = 50
EMPTY_MM = 400
PRODUCT_MM = 18
CAPACITY = round((EMPTY_MM - FULL_MM) / PRODUCT_MM)  # 20


def sensor_distance(units: int) -> float:
    """What the VL53L0X would report: median of 10 noisy readings, like the firmware does."""
    true_mm = EMPTY_MM - units * PRODUCT_MM
    samples = [true_mm + random.gauss(0, 3) for _ in range(10)]
    return round(statistics.median(samples), 1)


def units_from_fill(fill_percent: float | None) -> int:
    if fill_percent is None:
        return CAPACITY
    return round(fill_percent / 100 * CAPACITY)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    p.add_argument("--interval", type=float, default=5, help="Seconds between rounds")
    p.add_argument("--busy", action="store_true", help="Take products faster, to show changes quickly")
    p.add_argument(
        "--refill-chance", type=float, default=0.15, help="Chance an empty dispenser gets refilled each round"
    )
    p.add_argument("--skip", nargs="*", default=[], help="Dispenser IDs to leave silent (they'll go offline)")
    p.add_argument("--rounds", type=int, default=0, help="Stop after this many rounds (0 = run forever)")
    args = p.parse_args()

    base = args.url.rstrip("/")
    client = httpx.Client(timeout=90)  # a sleeping Render app can take ~1 minute to wake up

    dispensers = client.get(f"{base}/dispensers").raise_for_status().json()
    # Never fake readings for the real dispenser: its data comes from the Pico W.
    real = [d["id"] for d in dispensers if d.get("real")]
    units = {
        d["id"]: units_from_fill(d["fill_percent"])
        for d in dispensers
        if d["id"] not in args.skip and not d.get("real")
    }
    print(f"Simulating {len(units)} dispensers against {base}. Ctrl+C to stop.")
    if real:
        print(f"Leaving the real dispenser alone: {', '.join(real)}")
    print()

    max_taken = 3 if args.busy else 1
    take_chance = 0.6 if args.busy else 0.3

    rnd = 0
    while args.rounds == 0 or rnd < args.rounds:
        rnd += 1
        for dispenser_id in units:
            if units[dispenser_id] == 0 and random.random() < args.refill_chance:
                units[dispenser_id] = CAPACITY
                note = "refilled by staff"
            elif random.random() < take_chance:
                taken = random.randint(1, max_taken)
                units[dispenser_id] = max(0, units[dispenser_id] - taken)
                note = f"{taken} taken"
            else:
                note = ""

            r = client.post(
                f"{base}/readings",
                json={
                    "dispenser_id": dispenser_id,
                    "distance_mm": sensor_distance(units[dispenser_id]),
                    "battery_v": 3.8,
                },
                headers={"X-Device-Key": f"demo-{dispenser_id}"},
            )
            if r.status_code != 201:
                print(f"  {dispenser_id:<14} ERROR {r.status_code}: {r.text}")
                continue
            body = r.json()
            print(f"  {dispenser_id:<14} {body['fill_percent']:5.1f}%  {body['status']:<6} {note}")
        print(f"--- round {rnd} done, next in {args.interval:g}s ---\n")
        if args.rounds == 0 or rnd < args.rounds:
            time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
