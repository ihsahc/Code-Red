// Live API client with a local, matching demo fallback for presentations.
const apiBase = CONFIG.API_BASE_URL.replace(/\/$/, "");
let dispensers = [], buildings = new Map(), usingFallback = false, staffMode = false, highlightedName = null, youMarker, routeLine;
const markers = {};
const INFO = {
  full: { color: "green", symbol: "✓", label: "Well stocked" }, low: { color: "yellow", symbol: "~", label: "Running lower" },
  empty: { color: "red", symbol: "!", label: "Low or empty" }, offline: { color: "gray", symbol: "?", label: "Offline" },
};
const map = L.map("map", {
  minZoom: CONFIG.MAP_MIN_ZOOM,
  maxBounds: CONFIG.MAP_BOUNDS,
  maxBoundsViscosity: 1.0, // 1.0 = a hard wall: you can't drag outside campus
}).setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { minZoom: CONFIG.MAP_MIN_ZOOM, maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => { const el = document.createElement("div"); el.textContent = value ?? ""; return el.innerHTML; };
function timeAgo(iso) { if (!iso) return "never"; const s = Math.max(0, Math.round((Date.now() - new Date(iso)) / 1000)); return s < 5 ? "just now" : s < 60 ? `${s} sec ago` : `${Math.round(s / 60)} min ago`; }
function distance(a, b, c, d) { const r = (n) => n * Math.PI / 180, h = Math.sin(r(c - a) / 2) ** 2 + Math.cos(r(a)) * Math.cos(r(c)) * Math.sin(r(d - b) / 2) ** 2; return 12742000 * Math.asin(Math.sqrt(h)); }
function distanceText(m) { return `${m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`} away (about ${Math.max(1, Math.round(m / CONFIG.WALK_METERS_PER_MIN))} min walk)`; }

function fallbackData() {
  const now = Date.now();
  return DISPENSERS.map((d) => ({ id: d.id, building: { name: d.building, lat: d.lat, lng: d.lng }, floor: d.floor, location_note: "Women's restroom", fill_percent: d.fill, last_reading_at: new Date(d.offline ? now - 600000 : now).toISOString(), status: d.offline ? "offline" : d.fill > CONFIG.GREEN_ABOVE ? "full" : d.fill >= CONFIG.STOCKED_MIN ? "low" : "empty", demo: !CONFIG.REAL_DISPENSER_IDS.includes(d.id) }));
}
function normalize(d) { return { ...d, demo: !CONFIG.REAL_DISPENSER_IDS.includes(d.id) }; }
// Group dispensers by building. Each building becomes ONE pin whose color comes
// from its fullest floor: any floor stocked -> green/yellow, all empty -> red.
function groupBuildings() {
  const map = new Map();
  dispensers.forEach((d) => {
    const name = d.building.name;
    if (!map.has(name)) map.set(name, { name, lat: d.building.lat, lng: d.building.lng, floors: [] });
    map.get(name).floors.push(d);
  });
  map.forEach((b) => {
    b.floors.sort((x, y) => String(x.floor).localeCompare(String(y.floor), undefined, { numeric: true }));
    const online = b.floors.filter((f) => f.status !== "offline");
    b.best = online.length ? online.reduce((a, f) => ((f.fill_percent ?? 0) > (a.fill_percent ?? 0) ? f : a)) : null;
    b.status = b.best ? b.best.status : "offline"; // all floors offline -> gray
  });
  return map;
}
function icon(b) { const i = INFO[b.status], h = b.name === highlightedName ? " highlight" : ""; return L.divIcon({ className: "", html: `<div class="pin ${i.color}${h}">${i.symbol}</div>`, iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -16] }); }
function floorRow(f) { const i = INFO[f.status], pct = f.status === "offline" ? "No recent reading" : `${Math.round(f.fill_percent)}% · ${i.label}`; return `<li class="floor-row"><span class="dot ${i.color}">${i.symbol}</span><span class="floor-name">${escapeHtml(f.floor)}</span><span class="floor-pct">${pct}</span></li>`; }
function popup(b) {
  const latest = b.floors.map((f) => f.last_reading_at).filter(Boolean).sort().pop();
  const live = b.floors.some((f) => !f.demo);
  return `<div class="popup"><h3>${escapeHtml(b.name)}</h3><p class="hint">${b.floors.length} dispenser${b.floors.length === 1 ? "" : "s"} · pin shows the fullest floor</p><ul class="floor-list">${b.floors.map(floorRow).join("")}</ul><p>Updated ${timeAgo(latest)}</p><span class="badge ${live ? "real" : ""}">${live ? "Includes live dispenser" : "Demo data"}</span></div>`;
}
function render() {
  buildings = groupBuildings();
  buildings.forEach((b, name) => {
    if (!markers[name]) markers[name] = L.marker([b.lat, b.lng], { icon: icon(b) }).bindPopup(() => popup(buildings.get(name) || b)).addTo(map);
    else { markers[name].setIcon(icon(b)); if (markers[name].isPopupOpen()) markers[name].setPopupContent(popup(b)); }
  });
  Object.keys(markers).forEach((name) => { if (!buildings.has(name)) { map.removeLayer(markers[name]); delete markers[name]; } });
}
function fillBuildings() { const names = [...buildings.keys()].sort((a, b) => a.localeCompare(b)); $("building-select").innerHTML = '<option value="">Choose a building…</option>' + names.map((n) => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join(""); }
function result(html, warning = false) { $("result").innerHTML = html; $("result").classList.toggle("warn", warning); $("result").hidden = false; }
function clearHighlight() { highlightedName = null; if (routeLine) { map.removeLayer(routeLine); routeLine = null; } }
function nearest(lat, lng, label) {
  clearHighlight(); const choices = [...buildings.values()].filter((b) => b.status === "full" || b.status === "low").map((b) => ({ b, meters: distance(lat, lng, b.lat, b.lng) })).sort((a, b) => a.meters - b.meters);
  if (!choices.length) return result("<strong>No stocked dispensers right now.</strong><span>Every dispenser is low, empty, or offline.</span>", true);
  const best = choices[0]; highlightedName = best.b.name; render(); routeLine = L.polyline([[lat, lng], [best.b.lat, best.b.lng]], { color: "#0b3d91", weight: 3, dashArray: "6 8" }).addTo(map); map.fitBounds([[lat, lng], [best.b.lat, best.b.lng]], { padding: [60, 60], maxZoom: 18 }); markers[best.b.name].openPopup(); result(`<strong>${escapeHtml(best.b.name)}</strong><span>${escapeHtml(best.b.best.floor)} · ${Math.round(best.b.best.fill_percent)}% full · ${distanceText(best.meters)}${label ? ` from ${escapeHtml(label)}` : ""}</span>`);
}
function locationFallback() { $("fallback").hidden = false; result("<strong>Location is off.</strong><span>Pick your building and we'll find the nearest stocked dispenser.</span>", true); }

async function urgent() {
  if (!staffMode) return;
  // Empty dispensers first, then ones running low; oldest alert first within each group.
  let items = [];
  const rank = { empty: 0, low: 1 };
  try {
    if (usingFallback) throw Error();
    const r = await fetch(`${apiBase}/staff/alerts`); if (!r.ok) throw Error();
    // Show each dispenser's current fill, not the fill when the alert was raised.
    const current = Object.fromEntries(dispensers.map((d) => [d.id, d.fill_percent]));
    items = (await r.json()).map((a) => ({ level: a.level, building: a.building_name, floor: a.floor, fill: current[a.dispenser_id] ?? a.fill_percent, since: a.created_at }));
  } catch {
    items = dispensers.filter((d) => d.status === "empty" || d.status === "low").map((d) => ({ level: d.status, building: d.building.name, floor: d.floor, fill: d.fill_percent, since: d.last_reading_at }));
  }
  items = items.filter((d) => d.level in rank).sort((a, b) => rank[a.level] - rank[b.level] || new Date(a.since) - new Date(b.since));
  $("urgent-list").innerHTML = items.length ? items.map((d) => `<div class="urgent-item ${d.level}"><strong>${escapeHtml(d.building)}</strong><span>${d.level === "empty" ? "Empty" : "Running low"} · ${escapeHtml(d.floor)} · ${Math.round(d.fill)}% full · since ${timeAgo(d.since)}</span></div>`).join("") : "<p>Everything is stocked right now.</p>";
}
async function load() { try { const r = await fetch(`${apiBase}/dispensers`); if (!r.ok) throw Error(); dispensers = (await r.json()).map(normalize); usingFallback = false; $("data-source").textContent = "Live data"; } catch { dispensers = fallbackData(); usingFallback = true; $("data-source").textContent = "Demo fallback"; } render(); fillBuildings(); urgent(); }

$("find-btn").addEventListener("click", () => { if (!("geolocation" in navigator)) return locationFallback(); $("find-btn").disabled = true; $("find-btn").textContent = "Finding you…"; navigator.geolocation.getCurrentPosition((p) => { const { latitude, longitude } = p.coords; $("fallback").hidden = true; if (youMarker) map.removeLayer(youMarker); youMarker = L.circleMarker([latitude, longitude], { radius: 8, color: "#fff", weight: 3, fillColor: "#0b3d91", fillOpacity: 1 }).addTo(map).bindTooltip("You are here"); nearest(latitude, longitude, "you"); $("find-btn").disabled = false; $("find-btn").textContent = "Find nearest stocked (15%+)"; }, () => { locationFallback(); $("find-btn").disabled = false; $("find-btn").textContent = "Find nearest stocked (15%+)"; }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }); });
$("building-select").addEventListener("change", () => { const b = buildings.get($("building-select").value); if (b) nearest(b.lat, b.lng, b.name); });
$("view-btn").addEventListener("click", () => { if (prompt("Enter staff passcode") !== CONFIG.STAFF_PASSCODE) return; staffMode = true; $("view-btn").hidden = true; $("find-btn").hidden = true; $("staff-panel").hidden = false; urgent(); });
$("student-btn").addEventListener("click", () => { staffMode = false; $("view-btn").hidden = false; $("find-btn").hidden = false; $("staff-panel").hidden = true; });
load(); setInterval(load, CONFIG.POLL_INTERVAL_MS);