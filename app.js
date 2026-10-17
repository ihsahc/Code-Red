// Live API client with a local, matching demo fallback for presentations.
const apiBase = CONFIG.API_BASE_URL.replace(/\/$/, "");
let dispensers = [], usingFallback = false, staffMode = false, staffSort = "longest", staffLocation = null, userLocation = null, locationWatchId = null, highlightedId = null, youMarker, routeLine;
const markers = {};
const INFO = {
  full: { color: "green", symbol: "✓", label: "Well stocked" }, low: { color: "yellow", symbol: "~", label: "Running lower" },
  empty: { color: "red", symbol: "!", label: "Low or empty" }, offline: { color: "gray", symbol: "?", label: "Offline" },
};
const map = L.map("map").setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);
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
function icon(d) { const i = INFO[d.status], h = d.id === highlightedId ? " highlight" : ""; return L.divIcon({ className: "", html: `<div class="pin ${i.color}${h}">${i.symbol}</div>`, iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -16] }); }
function popup(d) { const i = INFO[d.status], fill = d.status === "offline" ? "<p>No recent reading</p>" : `<p><strong>${Math.round(d.fill_percent)}%</strong> full: ${i.label}</p>`; return `<div class="popup"><h3>${escapeHtml(d.building.name)}</h3><p>${escapeHtml(d.floor)} · ${escapeHtml(d.location_note)}</p>${fill}<p>Updated ${timeAgo(d.last_reading_at)}</p><span class="badge ${d.demo ? "" : "real"}">${d.demo ? "Demo data" : "Live dispenser"}</span></div>`; }
function render() { dispensers.forEach((d) => { if (!markers[d.id]) markers[d.id] = L.marker([d.building.lat, d.building.lng], { icon: icon(d) }).bindPopup(() => popup(dispensers.find((current) => current.id === d.id) || d)).addTo(map); else { markers[d.id].setIcon(icon(d)); if (markers[d.id].isPopupOpen()) markers[d.id].setPopupContent(popup(d)); } }); }
function fillBuildings() { const unique = [...new Map(dispensers.map((d) => [d.building.name, d])).values()].sort((a, b) => a.building.name.localeCompare(b.building.name)); $("building-select").innerHTML = '<option value="">Choose a building…</option>' + unique.map((d) => `<option value="${d.id}">${escapeHtml(d.building.name)}</option>`).join(""); }
function result(html, warning = false) { $("result").innerHTML = html; $("result").classList.toggle("warn", warning); $("result").hidden = false; $("clear-result").hidden = false; }
function clearHighlight() { highlightedId = null; if (routeLine) { map.removeLayer(routeLine); routeLine = null; } }
function clearNearestResult() { clearHighlight(); render(); $("result").hidden = true; $("clear-result").hidden = true; $("fallback").hidden = true; $("building-select").value = ""; }
function nearest(lat, lng, label) {
  clearHighlight(); const choices = dispensers.filter((d) => d.status === "full" || d.status === "low").map((d) => ({ d, meters: distance(lat, lng, d.building.lat, d.building.lng) })).sort((a, b) => a.meters - b.meters);
  if (!choices.length) return result("<strong>No stocked dispensers right now.</strong><span>Every dispenser is low, empty, or offline.</span>", true);
  const best = choices[0]; highlightedId = best.d.id; render(); routeLine = L.polyline([[lat, lng], [best.d.building.lat, best.d.building.lng]], { color: "#0b3d91", weight: 3, dashArray: "6 8" }).addTo(map); map.fitBounds([[lat, lng], [best.d.building.lat, best.d.building.lng]], { padding: [60, 60], maxZoom: 18 }); markers[best.d.id].openPopup(); result(`<strong>${escapeHtml(best.d.building.name)}</strong><span>${escapeHtml(best.d.floor)} · ${Math.round(best.d.fill_percent)}% full · ${distanceText(best.meters)}${label ? ` from ${escapeHtml(label)}` : ""}</span>`);
}
function locationFallback() { $("fallback").hidden = false; result("<strong>Location is off.</strong><span>Pick your building and we'll find the nearest stocked dispenser.</span>", true); }
function updateUserLocation(position) { const { latitude, longitude } = position.coords; userLocation = { lat: latitude, lng: longitude }; if (!youMarker) youMarker = L.circleMarker([latitude, longitude], { radius: 8, color: "#fff", weight: 3, fillColor: "#0b3d91", fillOpacity: 1 }).addTo(map).bindTooltip("You are here"); else youMarker.setLatLng([latitude, longitude]); if (staffSort === "closest") { staffLocation = userLocation; urgent(); } }
function watchUserLocation() { if (!("geolocation" in navigator) || locationWatchId !== null) return; locationWatchId = navigator.geolocation.watchPosition(updateUserLocation, () => { locationWatchId = null; }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }); }

async function urgent() {
  if (!staffMode) return;
  let empty = [];
  try { if (!usingFallback) { const r = await fetch(`${apiBase}/staff/alerts`); if (!r.ok) throw Error(); empty = (await r.json()).filter((a) => a.level === "empty").map((a) => { const dispenser = dispensers.find((d) => d.id === a.dispenser_id); return { building: a.building_name, floor: a.floor, fill: a.fill_percent, since: a.created_at, lat: dispenser?.building.lat, lng: dispenser?.building.lng }; }); } else throw Error(); } catch { empty = dispensers.filter((d) => d.status === "empty").map((d) => ({ building: d.building.name, floor: d.floor, fill: d.fill_percent, since: d.last_reading_at, lat: d.building.lat, lng: d.building.lng })); }
  if (staffSort === "closest" && staffLocation) empty.forEach((d) => { d.meters = distance(staffLocation.lat, staffLocation.lng, d.lat, d.lng); });
  empty.sort(staffSort === "closest" && staffLocation ? (a, b) => a.meters - b.meters : (a, b) => new Date(a.since) - new Date(b.since));
  $("urgent-list").innerHTML = empty.length ? empty.map((d) => `<div class="urgent-item"><strong>${escapeHtml(d.building)}</strong><span>${escapeHtml(d.floor)} · ${Math.round(d.fill)}% full · ${staffSort === "closest" && staffLocation ? distanceText(d.meters) : `empty ${timeAgo(d.since)}`}</span></div>`).join("") : "<p>Nothing is empty right now.</p>";
}
async function load() { try { const r = await fetch(`${apiBase}/dispensers`); if (!r.ok) throw Error(); dispensers = (await r.json()).map(normalize); usingFallback = false; $("data-source").textContent = "Live data"; } catch { dispensers = fallbackData(); usingFallback = true; $("data-source").textContent = "Demo fallback"; } render(); fillBuildings(); urgent(); }

$("find-btn").addEventListener("click", () => { if (!("geolocation" in navigator)) return locationFallback(); $("find-btn").disabled = true; $("find-btn").textContent = "Finding you…"; navigator.geolocation.getCurrentPosition((p) => { updateUserLocation(p); $("fallback").hidden = true; nearest(userLocation.lat, userLocation.lng, "you"); watchUserLocation(); $("find-btn").disabled = false; $("find-btn").textContent = "Find nearest stocked (15%+)"; }, () => { locationFallback(); $("find-btn").disabled = false; $("find-btn").textContent = "Find nearest stocked (15%+)"; }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }); });
$("building-select").addEventListener("change", () => { const d = dispensers.find((item) => item.id === $("building-select").value); if (d) nearest(d.building.lat, d.building.lng, d.building.name); });
$("clear-result").addEventListener("click", clearNearestResult);
$("view-btn").addEventListener("click", () => { if (prompt("Enter staff passcode") !== CONFIG.STAFF_PASSCODE) return; clearNearestResult(); staffMode = true; document.body.classList.add("staff-active"); $("view-btn").hidden = true; $("find-btn").hidden = true; $("staff-panel").hidden = false; urgent(); map.invalidateSize(); });
$("student-btn").addEventListener("click", () => { staffMode = false; document.body.classList.remove("staff-active"); $("view-btn").hidden = false; $("find-btn").hidden = false; $("staff-panel").hidden = true; map.invalidateSize(); });
$("sort-longest").addEventListener("click", () => { staffSort = "longest"; $("sort-longest").classList.add("active"); $("sort-closest").classList.remove("active"); urgent(); });
$("sort-closest").addEventListener("click", () => { if (!("geolocation" in navigator)) return result("<strong>Location is unavailable.</strong><span>Use the longest-empty sort instead.</span>", true); const useLocation = (position) => { updateUserLocation(position); staffLocation = userLocation; staffSort = "closest"; $("sort-closest").classList.add("active"); $("sort-longest").classList.remove("active"); urgent(); watchUserLocation(); }; if (userLocation) useLocation({ coords: { latitude: userLocation.lat, longitude: userLocation.lng } }); else navigator.geolocation.getCurrentPosition(useLocation, () => result("<strong>Location is off.</strong><span>Allow location to sort urgent refills by distance.</span>", true), { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }); });
watchUserLocation(); load(); setInterval(load, CONFIG.POLL_INTERVAL_MS);
