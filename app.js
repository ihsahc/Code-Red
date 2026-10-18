// Live API client with a local, matching demo fallback for presentations.
const apiBase = CONFIG.API_BASE_URL.replace(/\/$/, "");
let dispensers = [], buildings = new Map(), usingFallback = false, staffMode = false, staffSort = "longest", staffLocation = null, staffNote = "", highlightedName = null, youMarker, routeLine;
const markers = {};
// Each status gets a color (class in style.css) and an emoji, so color isn't the only cue.
const INFO = {
  full: { color: "st-full", symbol: "😎", label: "Well stocked" }, low: { color: "st-low", symbol: "😬", label: "Running lower" },
  empty: { color: "st-empty", symbol: "😱", label: "Low or empty" }, offline: { color: "st-offline", symbol: "💤", label: "Offline" },
};
const ROUTE_COLOR = "#833ab4"; // Instagram purple, for the "nearest" route and the you-are-here dot
const map = L.map("map", {
  minZoom: CONFIG.MAP_MIN_ZOOM,
  maxBounds: CONFIG.MAP_BOUNDS,
  maxBoundsViscosity: 1.0, // 1.0 = a hard wall: you can't drag outside campus
}).setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { minZoom: CONFIG.MAP_MIN_ZOOM, maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);
// 2016 "Instagram filter": a purple -> pink -> orange gradient laid over the map
// tiles but UNDER the pins (its own pane, between tiles and markers). style.css
// blends it into the map like a photo filter. It covers the whole campus area
// (MAP_BOUNDS), which is as far as the map can be dragged.
map.createPane("instaFilter").style.zIndex = 250;
const FILTER_GRADIENT = "data:image/svg+xml;utf8," + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" preserveAspectRatio="none">'
  + '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
  + '<stop offset="0" stop-color="#833ab4"/><stop offset="0.5" stop-color="#e1306c"/><stop offset="1" stop-color="#f77737"/>'
  + '</linearGradient></defs><rect width="10" height="10" fill="url(#g)"/></svg>');
L.imageOverlay(FILTER_GRADIENT, CONFIG.MAP_BOUNDS, { pane: "instaFilter", interactive: false }).addTo(map);
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => { const el = document.createElement("div"); el.textContent = value ?? ""; return el.innerHTML; };
function timeAgo(iso) { if (!iso) return "never"; const s = Math.max(0, Math.round((Date.now() - new Date(iso)) / 1000)); return s < 5 ? "just now" : s < 60 ? `${s} sec ago` : `${Math.round(s / 60)} min ago`; }
function distance(a, b, c, d) { const r = (n) => n * Math.PI / 180, h = Math.sin(r(c - a) / 2) ** 2 + Math.cos(r(a)) * Math.cos(r(c)) * Math.sin(r(d - b) / 2) ** 2; return 12742000 * Math.asin(Math.sqrt(h)); }
function distanceText(m) { return `${m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`} away (about ${Math.max(1, Math.round(m / CONFIG.WALK_METERS_PER_MIN))} min walk)`; }

// Stable made-up streak (1-31 days) for demo data, matching how the backend fakes them.
function demoStreak(id) { let h = 0; for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0; return (h % 31) + 1; }
function fallbackData() {
  const now = Date.now();
  return DISPENSERS.map((d) => {
    const status = d.offline ? "offline" : d.fill > CONFIG.GREEN_ABOVE ? "full" : d.fill >= CONFIG.STOCKED_MIN ? "low" : "empty";
    return { id: d.id, building: { name: d.building, lat: d.lat, lng: d.lng }, floor: d.floor, location_note: "Women's restroom", fill_percent: d.fill, last_reading_at: new Date(d.offline ? now - 600000 : now).toISOString(), status, streak_days: status === "empty" ? 0 : demoStreak(d.id), demo: !CONFIG.REAL_DISPENSER_IDS.includes(d.id) };
  });
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
function icon(b) { const i = INFO[b.status], h = b.name === highlightedName ? " highlight" : ""; return L.divIcon({ className: "", html: `<div class="pin ${i.color}${h}">${i.symbol}</div>`, iconSize: [34, 34], iconAnchor: [17, 17], popupAnchor: [0, -18] }); }
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
function result(html, warning = false) { $("result").innerHTML = html; $("result").classList.toggle("warn", warning); $("result").hidden = false; $("clear-result").hidden = false; }
function clearHighlight() { highlightedName = null; if (routeLine) { map.removeLayer(routeLine); routeLine = null; } }
// Same as pressing "Clear nearest result": remove the route, highlight and result box.
function clearNearest() { clearHighlight(); render(); $("result").hidden = true; $("clear-result").hidden = true; $("fallback").hidden = true; }
// A small pop-up alert at the top of the screen, with a Close button (also closes itself after 6 seconds).
let toastTimer;
function hideAlert() { const el = $("toast"); if (el) el.hidden = true; clearTimeout(toastTimer); }
function showAlert(title, text) {
  let el = $("toast");
  if (!el) { el = document.createElement("div"); el.id = "toast"; el.className = "toast"; el.setAttribute("role", "alert"); document.body.appendChild(el); }
  el.innerHTML = `<div class="toast-text"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(text)}</span></div><button type="button" class="toast-close">Close</button>`;
  el.querySelector(".toast-close").addEventListener("click", hideAlert);
  el.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(hideAlert, 6000);
}
function nearest(lat, lng, label) {
  clearHighlight(); const choices = [...buildings.values()].filter((b) => b.status === "full" || b.status === "low").map((b) => ({ b, meters: distance(lat, lng, b.lat, b.lng) })).sort((a, b) => a.meters - b.meters);
  if (!choices.length) return result("<strong>No stocked dispensers right now.</strong><span>Every dispenser is low, empty, or offline.</span>", true);
  const best = choices[0]; highlightedName = best.b.name; render(); routeLine = L.polyline([[lat, lng], [best.b.lat, best.b.lng]], { color: ROUTE_COLOR, weight: 4, dashArray: "6 8" }).addTo(map); map.fitBounds([[lat, lng], [best.b.lat, best.b.lng]], { padding: [60, 60], maxZoom: 18 }); markers[best.b.name].openPopup(); result(`<strong>${escapeHtml(best.b.name)}</strong><span>${escapeHtml(best.b.best.floor)} · ${Math.round(best.b.best.fill_percent)}% full · ${distanceText(best.meters)}${label ? ` from ${escapeHtml(label)}` : ""}</span>`);
}
function locationFallback() { $("fallback").hidden = false; result("<strong>Location is off.</strong><span>Pick your building and we'll find the nearest stocked dispenser.</span>", true); }

async function urgent() {
  if (!staffMode) return;
  // Only RED (empty) dispensers, one row per floor. Alerts tell us how long each has been empty.
  const since = {};
  if (!usingFallback) {
    try {
      const r = await fetch(`${apiBase}/staff/alerts`);
      if (r.ok) (await r.json()).filter((a) => a.level === "empty").forEach((a) => { if (!since[a.dispenser_id] || new Date(a.created_at) < new Date(since[a.dispenser_id])) since[a.dispenser_id] = a.created_at; });
    } catch { /* no alerts: fall back to the last reading time below */ }
  }
  const items = dispensers.filter((d) => d.status === "empty").map((d) => ({
    building: d.building.name, floor: d.floor, fill: d.fill_percent, since: since[d.id] || d.last_reading_at,
    meters: staffSort === "closest" && staffLocation ? distance(staffLocation.lat, staffLocation.lng, d.building.lat, d.building.lng) : null,
  }));
  const byLongest = (a, b) => new Date(a.since) - new Date(b.since); // empty the longest first
  items.sort(staffSort === "closest" && staffLocation ? (a, b) => a.meters - b.meters || byLongest(a, b) : byLongest);
  const note = staffNote ? `<p class="staff-note">${escapeHtml(staffNote)}</p>` : "";
  $("urgent-list").innerHTML = note + (items.length ? items.map((d) => `<div class="urgent-item empty"><strong>${escapeHtml(d.building)}</strong><span>${escapeHtml(d.floor)} · ${Math.round(d.fill)}% full · empty since ${timeAgo(d.since)}${d.meters != null ? ` · ${distanceText(d.meters)}` : ""}</span><span class="streak-lost">💔 Streak lost</span></div>`).join("") : "<p>No empty dispensers right now.</p>");
  renderStreaks();
}

// Snapchat-style streaks: days since each dispenser was last empty, longest first.
// Empty dispensers have lost their streak (shown above); offline ones are left out
// because a silent sensor can't prove it stayed stocked.
const STREAKS_SHOWN = 10;
let showAllStreaks = false;
function streakBadge(d) {
  const days = d.streak_days;
  const extra = (days >= 100 ? " 💯" : "") + (d.status === "low" ? " ⌛" : "");
  return `<span class="streak-count${d.status === "low" ? " at-risk" : ""}">🔥 ${days}${extra}</span>`;
}
function renderStreaks() {
  const list = dispensers
    .filter((d) => (d.status === "full" || d.status === "low") && d.streak_days != null)
    .sort((a, b) => b.streak_days - a.streak_days || a.building.name.localeCompare(b.building.name));
  const shown = showAllStreaks ? list : list.slice(0, STREAKS_SHOWN);
  $("streak-list").innerHTML = shown.length
    ? shown.map((d, i) => `<li class="streak-item"><span class="streak-rank">${i + 1}</span><span class="streak-name"><strong>${escapeHtml(d.building.name)}</strong><span>${escapeHtml(d.floor)} · ${Math.round(d.fill_percent)}% full · ${d.streak_days === 1 ? "1 day" : `${d.streak_days} days`}</span></span>${streakBadge(d)}</li>`).join("")
    : "<p>No streaks yet: they start once a dispenser reports in stocked.</p>";
  const more = $("streak-more");
  more.hidden = list.length <= STREAKS_SHOWN;
  more.textContent = showAllStreaks ? "Show top 10" : `Show all ${list.length}`;
}
function syncSortButtons() {
  [["sort-longest", "longest"], ["sort-closest", "closest"]].forEach(([id, mode]) => { $(id).classList.toggle("active", staffSort === mode); $(id).setAttribute("aria-pressed", String(staffSort === mode)); });
}
async function load() { try { const r = await fetch(`${apiBase}/dispensers`); if (!r.ok) throw Error(); dispensers = (await r.json()).map(normalize); usingFallback = false; $("data-source").textContent = "Live data"; } catch { dispensers = fallbackData(); usingFallback = true; $("data-source").textContent = "Demo fallback"; } render(); fillBuildings(); urgent(); }

$("find-btn").addEventListener("click", () => { if (!("geolocation" in navigator)) return locationFallback(); $("find-btn").disabled = true; $("find-btn").textContent = "Finding you…"; navigator.geolocation.getCurrentPosition((p) => { const { latitude, longitude } = p.coords; $("fallback").hidden = true; if (youMarker) map.removeLayer(youMarker); youMarker = L.circleMarker([latitude, longitude], { radius: 8, color: "#fff", weight: 3, fillColor: ROUTE_COLOR, fillOpacity: 1 }).addTo(map).bindTooltip("You are here"); nearest(latitude, longitude, "you"); $("find-btn").disabled = false; $("find-btn").textContent = "Find nearest stocked (15%+)"; }, () => { locationFallback(); $("find-btn").disabled = false; $("find-btn").textContent = "Find nearest stocked (15%+)"; }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }); });
$("building-select").addEventListener("change", () => { const b = buildings.get($("building-select").value); if (b) nearest(b.lat, b.lng, b.name); });
$("view-btn").addEventListener("click", () => {
  const code = prompt("Enter staff passcode");
  if (code === null) return; // they pressed Cancel: do nothing
  if (code !== CONFIG.STAFF_PASSCODE) return showAlert("Incorrect staff passcode", "Please try again, or keep using Student View.");
  hideAlert(); clearNearest(); // leave the student's "nearest stocked" result behind
  staffMode = true; $("view-btn").hidden = true; $("find-btn").hidden = true; $("staff-panel").hidden = false; urgent();
});
$("student-btn").addEventListener("click", () => { staffMode = false; $("view-btn").hidden = false; $("find-btn").hidden = false; $("staff-panel").hidden = true; });
$("sort-longest").addEventListener("click", () => { staffSort = "longest"; staffNote = ""; syncSortButtons(); urgent(); });
$("sort-closest").addEventListener("click", () => {
  const btn = $("sort-closest");
  const done = () => { btn.disabled = false; btn.textContent = "Closest to me"; syncSortButtons(); urgent(); };
  if (!("geolocation" in navigator)) { staffNote = "This browser can't share location, so showing longest empty first."; staffSort = "longest"; return done(); }
  btn.disabled = true; btn.textContent = "Locating…";
  navigator.geolocation.getCurrentPosition(
    (p) => { staffLocation = { lat: p.coords.latitude, lng: p.coords.longitude }; staffSort = "closest"; staffNote = ""; done(); },
    () => { staffNote = "Location is off, so showing longest empty first."; staffSort = "longest"; done(); },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
  );
});
$("clear-result").addEventListener("click", clearNearest);
$("streak-more").addEventListener("click", () => { showAllStreaks = !showAllStreaks; renderStreaks(); });
syncSortButtons();
load(); setInterval(load, CONFIG.POLL_INTERVAL_MS);