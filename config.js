// config.js — settings you might want to tweak. Change a value here, refresh the page, done.

const CONFIG = {
  // A dispenser turns gray ("offline") if its last reading is older than this.
  OFFLINE_AFTER_MS: 2 * 60 * 1000, // 2 minutes

  // Status cutoffs (fill percentage)
  GREEN_ABOVE: 50, // more than 50%  -> green
  STOCKED_MIN: 15, // 15% to 50%     -> yellow, below 15% -> red

  // Where the map starts (Georgia Tech campus) and how zoomed in it is.
  MAP_CENTER: [33.7756, -84.3985],
  MAP_ZOOM: 16,

  // How often the fake dispensers send a new "reading", in milliseconds.
  SIMULATION_INTERVAL_MS: 3000,

  // Used to turn distance into a rough walking time (about 80 meters per minute).
  WALK_METERS_PER_MIN: 80,
};
