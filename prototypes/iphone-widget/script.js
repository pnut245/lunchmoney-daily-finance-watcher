const SNAPSHOT_URL = "../../data/widget_snapshot.json";
const SETTINGS_URL = "../../data/settings.json";
const LEDGER_URL = "../../data/ledger.json";
const REFRESH_INTERVAL_MS = 60 * 1000;
const STORAGE_KEY = "one-number-today-portal-settings";

const DEFAULT_SETTINGS = {
  daily_allowance: 55,
  excluded_keywords: [
    "rent",
    "mortgage",
    "insurance",
    "utilities",
    "taxes",
    "transfer",
    "deposit",
    "loan payment",
    "credit card payment",
    "savings transfer",
    "reimbursement",
  ],
  preset_amounts: [5, 25, 55, 111],
  monthly_reset_day: 1,
  monthly_reset_time: "04:00",
  timezone: "America/Phoenix",
};

let snapshot = null;
let settings = DEFAULT_SETTINGS;
let ledger = [];

function moneyNumber(value) {
  const number = Number(value || 0);
  return Math.round(number).toLocaleString("en-US");
}

function formatUpdated(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function projections(amount) {
  const daily = Number(amount || 0);
  return [
    ["1 month", daily * 30],
    ["3 months", daily * 90],
    ["1 year", daily * 365],
    ["5 years", daily * 365 * 5],
    ["10 years", daily * 365 * 10],
  ];
}

async function loadJSON(url, fallback) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed: ${response.status}`);
    return await response.json();
  } catch {
    return fallback;
  }
}

async function bootstrap() {
  const remoteSettings = await loadJSON(SETTINGS_URL, DEFAULT_SETTINGS);
  const localSettings = loadLocalSettings();
  settings = { ...DEFAULT_SETTINGS, ...remoteSettings, ...localSettings };
  ledger = await loadJSON(LEDGER_URL, []);
  await refreshSnapshot();
  renderPortal();
  renderLedger();
  bindEvents();
  route();
  window.setInterval(refreshSnapshot, REFRESH_INTERVAL_MS);
}

function loadLocalSettings() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") || {};
  } catch {
    return {};
  }
}

function saveLocalSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

async function refreshSnapshot() {
  snapshot = await loadJSON(SNAPSHOT_URL, snapshot);
  renderDaily();
  renderPortalSnapshot();
}

function renderDaily() {
  const panel = document.getElementById("daily-view");
  const remaining = Number(snapshot?.remaining_today ?? settings.daily_allowance ?? 0);
  const isNegative = Boolean(snapshot?.is_negative ?? remaining < 0);
  panel.classList.toggle("negative", isNegative);
  document.getElementById("daily-number").textContent = moneyNumber(remaining);
  document.getElementById("daily-updated").textContent = `Updated ${formatUpdated(snapshot?.updated_at ?? snapshot?.last_updated)}`;
}

function renderPortal() {
  const grid = document.getElementById("allowance-grid");
  const selected = Number(settings.daily_allowance || 55);

  grid.innerHTML = settings.preset_amounts
    .map((amount) => {
      const value = Number(amount);
      return `
        <button
          class="allowance-card ${value === selected ? "selected" : ""}"
          type="button"
          data-allowance="${value}"
          role="radio"
          aria-checked="${value === selected}"
        >
          <div class="allowance-amount">${value}</div>
          <div class="allowance-label">per day</div>
        </button>
      `;
    })
    .join("");

  document.getElementById("custom-allowance").value = selected;
  document.getElementById("reset-day").value = settings.monthly_reset_day;
  document.getElementById("reset-time").value = settings.monthly_reset_time;

  document.getElementById("projection-list").innerHTML = projections(selected)
    .map(
      ([label, total]) => `
        <div class="projection-row">
          <span>${label}</span>
          <strong>$${Math.round(total).toLocaleString("en-US")}</strong>
        </div>
      `
    )
    .join("");

  renderKeywordChips();
}

function renderKeywordChips() {
  const list = document.getElementById("keyword-chip-list");
  list.innerHTML = settings.excluded_keywords
    .map(
      (keyword) => `
        <button class="chip" type="button" data-keyword="${keyword}">
          ${keyword} ×
        </button>
      `
    )
    .join("");
}

function renderPortalSnapshot() {
  document.getElementById("snapshot-status").textContent = snapshot
    ? "Live local snapshot is available."
    : "Snapshot unavailable. The daily view will fall back to the selected allowance.";
  document.getElementById("portal-remaining").textContent = moneyNumber(snapshot?.remaining_today ?? settings.daily_allowance);
  document.getElementById("portal-spent").textContent = moneyNumber(snapshot?.spent_today ?? snapshot?.today_discretionary_spend ?? 0);
  document.getElementById("portal-updated").textContent = formatUpdated(snapshot?.updated_at ?? snapshot?.last_updated);
}

function renderLedger() {
  const list = document.getElementById("ledger-list");
  const rows = ledger.length ? ledger : [];

  list.innerHTML = rows.length
    ? rows
        .map((entry) => {
          const value = Number(entry.month_result ?? entry.result ?? 0);
          return `
            <div class="ledger-row ${value < 0 ? "negative" : ""}">
              <span>${entry.month}</span>
              <strong>${value < 0 ? "-" : ""}${Math.abs(Math.round(value)).toLocaleString("en-US")}</strong>
            </div>
          `;
        })
        .join("")
    : `<div class="ledger-row"><span>No months closed yet</span><strong>--</strong></div>`;
}

function route() {
  const raw = window.location.hash.replace(/^#\//, "") || "daily";
  const view = ["daily", "portal", "ledger"].includes(raw) ? raw : "daily";
  document.querySelectorAll("[data-route-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.routePanel !== view;
  });
}

function bindEvents() {
  window.addEventListener("hashchange", route);

  document.getElementById("allowance-grid").addEventListener("click", (event) => {
    const button = event.target.closest("[data-allowance]");
    if (!button) return;
    settings.daily_allowance = Number(button.dataset.allowance);
    renderPortal();
  });

  document.getElementById("keyword-chip-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-keyword]");
    if (!button) return;
    settings.excluded_keywords = settings.excluded_keywords.filter((item) => item !== button.dataset.keyword);
    renderKeywordChips();
  });

  document.getElementById("keyword-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.getElementById("keyword-input");
    const value = input.value.trim().toLowerCase();
    if (!value) return;
    if (!settings.excluded_keywords.includes(value)) {
      settings.excluded_keywords = [...settings.excluded_keywords, value];
      renderKeywordChips();
    }
    input.value = "";
  });

  document.getElementById("save-settings").addEventListener("click", () => {
    settings.daily_allowance = Number(document.getElementById("custom-allowance").value || settings.daily_allowance || 55);
    settings.monthly_reset_day = Number(document.getElementById("reset-day").value || 1);
    settings.monthly_reset_time = document.getElementById("reset-time").value || "04:00";
    saveLocalSettings();
    renderPortal();
    renderDaily();
    renderPortalSnapshot();
  });

  document.getElementById("refresh-snapshot").addEventListener("click", refreshSnapshot);
}

bootstrap();
