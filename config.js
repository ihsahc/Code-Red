// config.js — settings you might want to tweak. Change a value here, refresh the page, done.

const CONFIG = {
  // Backend URL. Picked automatically: the local backend when the page is
  // opened on localhost, the live Render backend everywhere else.
  API_BASE_URL: ["localhost", "127.0.0.1"].includes(location.hostname)
    ? "http://localhost:8001"
    : "https://code-red-api.onrender.com",

  // The one physical Pico W dispenser. All other seeded devices are clearly
  // labelled as demo data in the map popup.
  REAL_DISPENSER_IDS: ["klaus-atrium-pico-w"],
  STAFF_PASSCODE: "GTSTAFF", // Demo-only browser check; not real security.

  // A dispenser turns gray ("offline") if its last reading is older than this.
  OFFLINE_AFTER_MS: 2 * 60 * 1000, // 2 minutes

  // Status cutoffs (fill percentage)
  GREEN_ABOVE: 50, // more than 50%  -> green
  STOCKED_MIN: 15, // 15% to 50%     -> yellow, below 15% -> red

  // Where the map starts (Georgia Tech campus) and how zoomed in it is.
  MAP_CENTER: [33.7756, -84.3985],
  MAP_ZOOM: 16,

  // Poll the live API and refresh local demo fallback data every 5 seconds.
  POLL_INTERVAL_MS: 5000,

  // Used to turn distance into a rough walking time (about 80 meters per minute).
  WALK_METERS_PER_MIN: 80,
};
