// South Bay Surf Report - frontend logic.
// Talks to the Flask API in app.py, which wraps core.py.

const grid = document.getElementById("spot-grid");
const statusBanner = document.getElementById("status-banner");
const todayDateEl = document.getElementById("today-date");

const overlay = document.getElementById("detail-overlay");
const detailTitle = document.getElementById("detail-title");
const detailTableBody = document.querySelector("#detail-table tbody");
const closeBtn = document.getElementById("detail-close");

function updateTodayDate() {
  todayDateEl.textContent = new Date().toLocaleDateString(undefined, {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });
}

updateTodayDate();
// Re-check every minute so the header rolls over to the new date at midnight
// without needing a manual page refresh.
setInterval(updateTodayDate, 60 * 1000);

function metersToFeet(m) {
  if (m === null || m === undefined) return null;
  return m * 3.28084;
}

function fmtFeet(m, decimals = 1) {
  const ft = metersToFeet(m);
  return ft === null ? "--" : ft.toFixed(decimals);
}

function degToCompass(deg) {
  if (deg === null || deg === undefined) return "--";
  const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  const idx = Math.round(deg / 22.5) % 16;
  return dirs[idx];
}

function fmtTideTime(timeStr) {
  // timeStr like "2026-07-11 14:32"
  const d = new Date(timeStr.replace(" ", "T"));
  if (isNaN(d.getTime())) return timeStr;
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function fmtDateHeading(dateStr) {
  // dateStr like "2026-07-11"
  const d = new Date(dateStr + "T00:00:00");
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function nextTide(tideEvents) {
  if (!tideEvents || tideEvents.length === 0) return null;
  const now = new Date();
  const upcoming = tideEvents
    .map(t => ({ ...t, when: new Date(t.time.replace(" ", "T")) }))
    .filter(t => t.when >= now)
    .sort((a, b) => a.when - b.when);
  return upcoming[0] || tideEvents[tideEvents.length - 1];
}

function showError(message) {
  statusBanner.textContent = message;
  statusBanner.hidden = false;
}

function renderCard(report) {
  const card = document.createElement("div");
  card.className = "spot-card";
  card.dataset.spotId = report.spot_id;

  const forecast = report.forecast || {};
  const buoy = report.nearby_buoy || {};
  const upcoming = nextTide(report.tide_today);

  const waveHeightM = forecast.wave_height ?? buoy.wave_height_m ?? null;
  const swellDir = forecast.swell_wave_direction ?? buoy.mean_wave_direction_deg ?? null;
  const swellPeriod = forecast.swell_wave_period ?? buoy.dominant_wave_period_s ?? null;

  card.innerHTML = `
    <h3>${report.spot}</h3>
    <div class="wave-row">
      <div class="compass">
        <div class="compass-arrow" style="transform: translateX(-50%) rotate(${swellDir ?? 0}deg);"></div>
      </div>
      <div class="wave-figures">
        <div class="wave-height">${fmtFeet(waveHeightM)} ft</div>
        <div class="wave-sub">Swell ${degToCompass(swellDir)} &middot; ${swellPeriod ?? "--"}s period</div>
      </div>
    </div>
    <div class="card-meta">
      <span>Water: <strong>${buoy.water_temp_c != null ? (buoy.water_temp_c * 9/5 + 32).toFixed(0) + "&deg;F" : "--"}</strong></span>
      <span>Next tide: <strong>${upcoming ? `${upcoming.type} ${upcoming.height_ft}ft @ ${fmtTideTime(upcoming.time)}` : "--"}</strong></span>
    </div>
    <div class="view-forecast">View 5-day forecast &rarr;</div>
  `;

  card.addEventListener("click", () => openDetail(report.spot_id, report.spot));
  return card;
}

async function loadDashboard() {
  try {
    const res = await fetch("/api/conditions");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load conditions");

    grid.innerHTML = "";
    data.forEach(report => grid.appendChild(renderCard(report)));
  } catch (err) {
    showError(`Couldn't load live conditions (${err.message}). Check your network connection - this app calls NOAA and Open-Meteo directly.`);
  }
}

async function openDetail(spotId, spotName) {
  detailTitle.textContent = spotName;
  detailTableBody.innerHTML = `<tr><td colspan="5">Loading...</td></tr>`;
  overlay.hidden = false;

  try {
    const res = await fetch(`/api/forecast/${spotId}?days=5`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load forecast");

    detailTableBody.innerHTML = "";
    data.days.forEach(day => {
      const tideChips = (day.tides || [])
        .map(t => `<span class="tide-chip ${t.type === "Low" ? "low" : ""}">${t.type} ${t.height_ft}ft @ ${fmtTideTime(t.time)}</span>`)
        .join("");

      const wind = day.wind || {};
      const windCell = wind.wind_speed_mph != null
        ? `${degToCompass(wind.wind_direction_deg)} (${Math.round(wind.wind_direction_deg)}&deg;) &middot; ${Math.round(wind.wind_speed_mph)} mph${wind.wind_gust_mph != null ? ` (g${Math.round(wind.wind_gust_mph)})` : ""}`
        : "--";

      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${fmtDateHeading(day.date)}</td>
        <td>${fmtFeet(day.wave_height_min_m, 0)}-${fmtFeet(day.wave_height_max_m, 0)} ft</td>
        <td>${degToCompass(day.swell_direction_deg)}${day.swell_direction_deg != null ? ` (${Math.round(day.swell_direction_deg)}&deg;)` : ""} &middot; ${day.swell_period_s ?? "--"}s &middot; ${fmtFeet(day.swell_height_m)}ft</td>
        <td>${windCell}</td>
        <td>${tideChips || "--"}</td>
      `;
      detailTableBody.appendChild(row);
    });
  } catch (err) {
    detailTableBody.innerHTML = `<tr><td colspan="5">Couldn't load forecast (${err.message})</td></tr>`;
  }
}

closeBtn.addEventListener("click", () => { overlay.hidden = true; });
overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.hidden = true; });

loadDashboard();
