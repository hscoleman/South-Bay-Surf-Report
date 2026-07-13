// South Bay Surf Report - frontend logic.
// Talks to the Flask API in app.py, which wraps core.py.

const grid = document.getElementById("spot-grid");
const statusBanner = document.getElementById("status-banner");
const todayDateEl = document.getElementById("today-date");
const bestSpotBanner = document.getElementById("best-spot-banner");

const overlay = document.getElementById("detail-overlay");
const detailTitle = document.getElementById("detail-title");
const detailTableBody = document.querySelector("#detail-table tbody");
const closeBtn = document.getElementById("detail-close");
const weekTrendEl = document.getElementById("week-trend");

const guideOverlay = document.getElementById("guide-overlay");
const guideTitle = document.getElementById("guide-title");
const guideContent = document.getElementById("guide-content");
const guideCloseBtn = document.getElementById("guide-close");

const skillButtons = document.querySelectorAll(".skill-btn");
const VALID_SKILLS = ["beginner", "intermediate", "advanced"];
let currentSkill = localStorage.getItem("southbaySurfSkill");
if (!VALID_SKILLS.includes(currentSkill)) currentSkill = "intermediate";

function applySkillButtonStyles() {
  skillButtons.forEach(btn => {
    btn.classList.toggle("active", btn.dataset.skill === currentSkill);
  });
}

function setSkill(skill) {
  if (!VALID_SKILLS.includes(skill) || skill === currentSkill) return;
  currentSkill = skill;
  localStorage.setItem("southbaySurfSkill", currentSkill);
  applySkillButtonStyles();
  loadDashboard();
}

skillButtons.forEach(btn => {
  btn.addEventListener("click", () => setSkill(btn.dataset.skill));
});
applySkillButtonStyles();

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

function fmtSunTime(isoStr) {
  if (!isoStr) return "--";
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return "--";
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

const QUALITY_CLASS = { Great: "badge-great", Good: "badge-good", Fair: "badge-fair", Poor: "badge-poor" };
const WIND_CLASS = { Offshore: "wind-offshore", "Cross-shore": "wind-cross", Onshore: "wind-onshore" };
const SWELL_CLASS = { Groundswell: "swell-ground", "Mixed swell": "swell-mixed", "Wind swell": "swell-wind" };

function qualityBadge(quality) {
  if (!quality) return "";
  const cls = QUALITY_CLASS[quality.rating] || "";
  const stars = "&#9733;".repeat(quality.stars) + "&#9734;".repeat(5 - quality.stars);
  return `<span class="quality-badge ${cls}">${quality.rating}<span class="stars">${stars}</span></span>`;
}

function windBadge(windQuality) {
  if (!windQuality) return "";
  const cls = WIND_CLASS[windQuality] || "";
  return `<span class="tag-badge ${cls}">${windQuality}</span>`;
}

function swellTypeBadge(swellType) {
  if (!swellType) return "";
  const cls = SWELL_CLASS[swellType] || "";
  return `<span class="tag-badge ${cls}">${swellType}</span>`;
}

// Builds a minimal inline SVG sparkline from an array of numbers (nulls are
// skipped). No charting library needed - just a normalized polyline.
function buildSparkline(values, cssClass, w = 100, h = 32, padding = 4) {
  const points = values
    .map((v, i) => ({ v, i }))
    .filter(p => p.v !== null && p.v !== undefined && !isNaN(p.v));
  if (points.length < 2) return "";

  const vals = points.map(p => p.v);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = (max - min) || 1;
  const stepX = (w - padding * 2) / (values.length - 1 || 1);

  const coords = points
    .map(p => {
      const x = padding + p.i * stepX;
      const y = padding + (h - padding * 2) * (1 - (p.v - min) / range);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return `<svg viewBox="0 0 ${w} ${h}" class="sparkline ${cssClass}" preserveAspectRatio="none">
    <polyline points="${coords}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" />
  </svg>`;
}

function renderCard(report) {
  const card = document.createElement("div");
  card.className = "spot-card";
  card.dataset.spotId = report.spot_id;

  const forecast = report.forecast || {};
  const buoy = report.nearby_buoy || {};
  const wind = report.wind || {};
  const upcoming = nextTide(report.tide_today);

  const waveHeightM = forecast.wave_height ?? buoy.wave_height_m ?? null;
  const swellDir = forecast.swell_wave_direction ?? buoy.mean_wave_direction_deg ?? null;
  const swellPeriod = forecast.swell_wave_period ?? buoy.dominant_wave_period_s ?? null;

  card.innerHTML = `
    <div class="card-head">
      <h3>${report.spot}</h3>
      ${qualityBadge(report.quality)}
    </div>
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
      <span>${windBadge(report.wind_quality)} ${wind.wind_speed_kt != null ? Math.round(wind.wind_speed_kt) + " kt" : ""}</span>
      <span>Water: <strong>${buoy.water_temp_c != null ? (buoy.water_temp_c * 9/5 + 32).toFixed(0) + "&deg;F" : "--"}</strong></span>
    </div>
    <div class="card-meta">
      <span>Next tide: <strong>${upcoming ? `${upcoming.type} ${upcoming.height_ft}ft @ ${fmtTideTime(upcoming.time)}` : "--"}</strong></span>
    </div>
    <div class="view-forecast">View 5-day forecast &rarr;</div>
    <div class="view-forecast view-guide">What makes ${report.spot} shine &rarr;</div>
  `;

  card.addEventListener("click", () => openDetail(report.spot_id, report.spot));

  // The guide line opens a different overlay - stop the click from also
  // bubbling up to the card's own listener (which would pop open both).
  const guideLink = card.querySelector(".view-guide");
  guideLink.addEventListener("click", (e) => {
    e.stopPropagation();
    openGuide(report.spot_id, report.spot);
  });

  return card;
}

function renderBestSpot(data) {
  const ranked = data
    .filter(r => r.quality)
    .slice()
    .sort((a, b) => b.quality.score - a.quality.score);

  if (ranked.length === 0) {
    bestSpotBanner.innerHTML = "";
    return;
  }

  const top = ranked[0];
  const rest = ranked.slice(1);
  const tideState = top.tide_state || {};

  const reasonBits = [];
  if (top.swell_type) reasonBits.push(swellTypeBadge(top.swell_type));
  if (top.wind_quality) reasonBits.push(windBadge(top.wind_quality));
  if (tideState.bucket) {
    reasonBits.push(`<span class="tag-badge tide-tag">${tideState.bucket} tide${tideState.trend ? ", " + tideState.trend : ""}</span>`);
  }

  const restRows = rest
    .map((r, i) => `
      <div class="rank-row">
        <span class="rank-num">#${i + 2}</span>
        <span class="rank-name">${r.spot}</span>
        ${qualityBadge(r.quality)}
      </div>
    `)
    .join("");

  bestSpotBanner.innerHTML = `
    <div class="best-spot-card">
      <div class="best-spot-label">&#127942; Best spot right now</div>
      <div class="best-spot-name">${top.spot}</div>
      <div class="best-spot-reasons">${reasonBits.join(" ")}</div>
      <div class="best-spot-note">Ranked from current wave height, swell direction match, wind, and tide for each spot's known sweet spot.</div>
    </div>
    <div class="rank-list">${restRows}</div>
  `;
}

async function loadDashboard() {
  try {
    const res = await fetch(`/api/conditions?skill=${currentSkill}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load conditions");

    grid.innerHTML = "";
    data.forEach(report => grid.appendChild(renderCard(report)));
    renderBestSpot(data);
  } catch (err) {
    showError(`Couldn't load live conditions (${err.message}). Check your network connection - this app calls NOAA and Open-Meteo directly.`);
  }
}

async function openDetail(spotId, spotName) {
  detailTitle.textContent = spotName;
  detailTableBody.innerHTML = `<tr><td colspan="6">Loading...</td></tr>`;
  weekTrendEl.innerHTML = "";
  overlay.hidden = false;

  try {
    const res = await fetch(`/api/forecast/${spotId}?days=5&skill=${currentSkill}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load forecast");

    // Week-at-a-glance wave height trend, above the table.
    const trendValues = data.days.map(d => metersToFeet(d.wave_height_max_m));
    const trendSpark = buildSparkline(trendValues, "sparkline-wave", 280, 46);
    weekTrendEl.innerHTML = trendSpark
      ? `<div class="week-trend-label">Wave height trend (this week)</div>${trendSpark}`
      : "";

    detailTableBody.innerHTML = "";
    data.days.forEach(day => {
      const tideChips = (day.tides || [])
        .map(t => `<span class="tide-chip ${t.type === "Low" ? "low" : ""}">${t.type} ${t.height_ft}ft @ ${fmtTideTime(t.time)}</span>`)
        .join("");
      const tideSpark = buildSparkline((day.tide_curve || []).map(p => p.height_ft), "sparkline-tide", 100, 28);

      const wind = day.wind || {};
      const windCell = wind.wind_speed_kt != null
        ? `${windBadge(day.wind_quality)}<br>${degToCompass(wind.wind_direction_deg)} (${Math.round(wind.wind_direction_deg)}&deg;) &middot; ${Math.round(wind.wind_speed_kt)} kt${wind.wind_gust_kt != null ? ` (g${Math.round(wind.wind_gust_kt)})` : ""}`
        : "--";

      const row = document.createElement("tr");
      row.innerHTML = `
        <td>
          ${fmtDateHeading(day.date)}
          <div class="sun-row">&#127749; ${fmtSunTime(day.sunrise)} &middot; &#127751; ${fmtSunTime(day.sunset)}</div>
        </td>
        <td>${qualityBadge(day.quality)}</td>
        <td>${fmtFeet(day.wave_height_min_m, 0)}-${fmtFeet(day.wave_height_max_m, 0)} ft</td>
        <td>
          ${swellTypeBadge(day.swell_type)}<br>
          ${degToCompass(day.swell_direction_deg)}${day.swell_direction_deg != null ? ` (${Math.round(day.swell_direction_deg)}&deg;)` : ""} &middot; ${day.swell_period_s ?? "--"}s &middot; ${fmtFeet(day.swell_height_m)}ft
        </td>
        <td>${windCell}</td>
        <td>
          ${tideSpark}
          <div class="tide-chips">${tideChips || "--"}</div>
        </td>
      `;
      detailTableBody.appendChild(row);
    });
  } catch (err) {
    detailTableBody.innerHTML = `<tr><td colspan="6">Couldn't load forecast (${err.message})</td></tr>`;
  }
}

async function openGuide(spotId, spotName) {
  guideTitle.textContent = `What makes ${spotName} shine`;
  guideContent.innerHTML = `<p class="guide-loading">Loading...</p>`;
  guideOverlay.hidden = false;

  try {
    const res = await fetch(`/api/guide/${spotId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "No guide available for this spot yet");

    guideContent.innerHTML = `
      <div class="guide-facts">
        <div class="guide-fact">
          <div class="guide-fact-label">Optimal swell</div>
          <div class="guide-fact-value">${data.optimal_swell}</div>
        </div>
        <div class="guide-fact">
          <div class="guide-fact-label">Optimal wind</div>
          <div class="guide-fact-value">${data.optimal_wind}</div>
        </div>
        <div class="guide-fact">
          <div class="guide-fact-label">Best tide</div>
          <div class="guide-fact-value">${data.best_tide}</div>
        </div>
        <div class="guide-fact">
          <div class="guide-fact-label">Best season</div>
          <div class="guide-fact-value">${data.best_season}</div>
        </div>
      </div>
      <p class="guide-blurb">${data.blurb}</p>
      <p class="guide-caveat">This is general spot knowledge compiled from public surf guides, not live data - sandbars shift, so always cross-check it against the live forecast above.</p>
    `;
  } catch (err) {
    guideContent.innerHTML = `<p class="guide-loading">Couldn't load this spot's guide (${err.message}).</p>`;
  }
}

closeBtn.addEventListener("click", () => { overlay.hidden = true; });
overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.hidden = true; });

guideCloseBtn.addEventListener("click", () => { guideOverlay.hidden = true; });
guideOverlay.addEventListener("click", (e) => { if (e.target === guideOverlay) guideOverlay.hidden = true; });

loadDashboard();
