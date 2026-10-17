// app.js — the logic: draws the map, colors the pins, fakes live data,
// and finds the nearest stocked dispenser.

// ---------- 1. Set up dispensers with live fields ----------
// Copy each dispenser from data.js and add fields that change over time.
const now0 = Date.now();
const dispensers = DISPENSERS.map((d) => ({
  ...d,
  // Offline fake dispensers get an old timestamp so they show as gray.
  lastReading: d.offline ? now0 - 10 * 60 * 1000 : now0,
  statusChangedAt: now0,
  status: null,
}));

// ---------- 2. Status logic ----------
function computeStatus(d) {
  const stale = Date.now() - d.lastReading > CONFIG.OFFLINE_AFTER_MS;
  if (stale) return "gray";
  if (d.fill > CONFIG.GREEN_ABOVE) return "green";
  if (d.fill >= CONFIG.STOCKED_MIN) return "yellow";
  return "red";
}

const STATUS_INFO = {
  green:  { symbol: "✓", label: "Well stocked" },
  yellow: { symbol: "~", label: "Running lower" },
  red:    { symbol: "!", label: "Low or empty" },
  gray:   { symbol: "?", label: "Offline" },
};

// ---------- 3. Small helpers ----------
function escapeHtml(text) {
  const el = document.createElement("div");
  el.textContent = text;
  return el.innerHTML;
}

function timeAgo(ms) {
  const sec = Math.round((Date.now() - ms) / 1000);
  if (sec < 5) return "just now";
  if (sec < 60) return sec + " sec ago";
  return Math.round(sec / 60) + " min ago";
}

// Distance between two lat/lng points, in meters (haversine formula).
function distanceMeters(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function formatDistance(m) {
  const mins = Math.max(1, Math.round(m / CONFIG.WALK_METERS_PER_MIN));
  const dist = m < 1000 ? Math.round(m) + " m" : (m / 1000).toFixed(1) + " km";
  return dist + " away (about " + mins + " min walk)";
}

// ---------- 4. Map and pins ----------
const map = L.map("map").setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const markers = {};        // id -> Leaflet marker
let highlightedId = null;  // which pin is the "nearest" result

function pinIcon(d) {
  const info = STATUS_INFO[d.status];
  const extra = d.id === highlightedId ? " highlight" : "";
  return L.divIcon({
    className: "",
    html: `<div class="pin ${d.status}${extra}">${info.symbol}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -16],
  });
}

function popupHtml(d) {
  const info = STATUS_INFO[d.status];
  const fillLine =
    d.status === "gray"
      ? "<p>No recent reading</p>"
      : `<p><strong>${Math.round(d.fill)}%</strong> full: ${info.label}</p>`;
  return `
    <div class="popup">
      <h3>${escapeHtml(d.building)}</h3>
      <p>${escapeHtml(d.floor)}</p>
      ${fillLine}
      <p>Updated ${timeAgo(d.lastReading)}</p>
      ${d.demo ? '<span class="badge">Demo data</span>' : ""}
    </div>`;
}

// Recompute every status, then redraw pins and popups.
function render() {
  for (const d of dispensers) {
    const newStatus = computeStatus(d);
    if (newStatus !== d.status) {
      d.status = newStatus;
      d.statusChangedAt = Date.now(); // used later for "red the longest"
    }
    if (!markers[d.id]) {
      markers[d.id] = L.marker([d.lat, d.lng], { icon: pinIcon(d) })
        .bindPopup(() => popupHtml(d))
        .addTo(map);
    } else {
      markers[d.id].setIcon(pinIcon(d));
      if (markers[d.id].isPopupOpen()) markers[d.id].setPopupContent(popupHtml(d));
    }
  }
}

// ---------- 5. Fake live data ----------
// Every few seconds each fake dispenser "reports in": its timestamp refreshes
// (so it doesn't turn gray) and its fill drifts down a little.
// Dispensers marked offline: true never report, so they stay gray.
function simulateTick() {
  for (const d of dispensers) {
    if (!d.demo || d.offline) continue;
    d.lastReading = Date.now();
    if (Math.random() < 0.3) d.fill = Math.max(0, d.fill - Math.random() * 2);
    if (d.fill < 3 && Math.random() < 0.2) d.fill = 100; // pretend staff refilled it
  }
  render();
}

// ---------- 6. Find nearest stocked ----------
const findBtn = document.getElementById("find-btn");
const fallbackBox = document.getElementById("fallback");
const buildingSelect = document.getElementById("building-select");
const resultBox = document.getElementById("result");

let youMarker = null;
let routeLine = null;

// Fill the building dropdown (used only if location is denied).
function fillBuildingDropdown() {
  const sorted = [...dispensers].sort((a, b) => a.building.localeCompare(b.building));
  buildingSelect.innerHTML =
    '<option value="">Choose a building…</option>' +
    sorted.map((d) => `<option value="${d.id}">${escapeHtml(d.building)}</option>`).join("");
}

function showResult(html, warn) {
  resultBox.innerHTML = html;
  resultBox.classList.toggle("warn", !!warn);
  resultBox.hidden = false;
}

function clearHighlight() {
  highlightedId = null;
  if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
}

// Given a spot (lat/lng), find and show the nearest dispenser that is green or yellow.
function showNearest(lat, lng, label) {
  clearHighlight();

  const stocked = dispensers.filter((d) => d.status === "green" || d.status === "yellow");
  if (stocked.length === 0) {
    showResult("<strong>No stocked dispensers right now.</strong><span>Every dispenser is low or offline.</span>", true);
    render();
    return;
  }

  let best = null;
  let bestDist = Infinity;
  for (const d of stocked) {
    const dist = distanceMeters(lat, lng, d.lat, d.lng);
    if (dist < bestDist) { best = d; bestDist = dist; }
  }

  highlightedId = best.id;
  render();

  routeLine = L.polyline([[lat, lng], [best.lat, best.lng]], {
    color: "#0b3d91", weight: 3, dashArray: "6 8",
  }).addTo(map);

  map.fitBounds([[lat, lng], [best.lat, best.lng]], { padding: [60, 60], maxZoom: 18 });
  markers[best.id].openPopup();

  showResult(
    `<strong>${escapeHtml(best.building)}</strong>
     <span>${escapeHtml(best.floor)} · ${Math.round(best.fill)}% full · ${formatDistance(bestDist)}${label ? " from " + escapeHtml(label) : ""}</span>`
  );
}

function useBuildingFallback() {
  fallbackBox.hidden = false;
  showResult("<strong>Location is off.</strong><span>Pick your building below and we'll find the nearest one.</span>", true);
}

findBtn.addEventListener("click", () => {
  if (!("geolocation" in navigator)) { useBuildingFallback(); return; }

  findBtn.disabled = true;
  findBtn.textContent = "Finding you…";

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      // We use the position right now and do NOT save it anywhere.
      const { latitude, longitude } = pos.coords;
      fallbackBox.hidden = true;

      if (youMarker) map.removeLayer(youMarker);
      youMarker = L.circleMarker([latitude, longitude], {
        radius: 8, color: "#fff", weight: 3, fillColor: "#0b3d91", fillOpacity: 1,
      }).addTo(map).bindTooltip("You are here");

      showNearest(latitude, longitude, "you");
      findBtn.disabled = false;
      findBtn.textContent = "Find nearest stocked (15%+)";
    },
    () => {
      useBuildingFallback();
      findBtn.disabled = false;
      findBtn.textContent = "Find nearest stocked (15%+)";
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
});

buildingSelect.addEventListener("change", () => {
  const chosen = dispensers.find((d) => d.id === buildingSelect.value);
  if (chosen) showNearest(chosen.lat, chosen.lng, chosen.building);
});

// ---------- 7. Start everything ----------
fillBuildingDropdown();
render();
setInterval(simulateTick, CONFIG.SIMULATION_INTERVAL_MS);
