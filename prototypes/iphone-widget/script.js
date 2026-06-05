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
let saveState = "saved";

const OBJECT_ART = {
  coffee: `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="44" y="42" width="62" height="80" rx="10" fill="#F4E1C8"/>
      <path d="M106 55H120C128 55 134 61 134 69C134 77 128 83 120 83H112" stroke="#171717" stroke-width="6" stroke-linecap="round"/>
      <path d="M56 42H95L108 56H44L56 42Z" fill="#1A1A1A"/>
      <ellipse cx="76" cy="122" rx="40" ry="10" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
  lunch: `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 94C32 75 47 60 66 60H107C124 60 138 74 138 91V101C138 111 130 119 120 119H50C40 119 32 111 32 101V94Z" fill="#E7B668"/>
      <path d="M42 66H132L116 99H58L42 66Z" fill="#D78A2B"/>
      <path d="M62 74C72 65 84 64 96 72C107 79 117 78 126 70" stroke="#6CBE45" stroke-width="8" stroke-linecap="round"/>
      <ellipse cx="84" cy="126" rx="42" ry="9" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
  groceries: `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M49 51H111L104 120H56L49 51Z" fill="#C99B63"/>
      <path d="M61 51C61 39 69 31 80 31C91 31 99 39 99 51" stroke="#171717" stroke-width="6" stroke-linecap="round"/>
      <rect x="68" y="58" width="13" height="30" rx="6.5" fill="#86BC4B"/>
      <circle cx="94" cy="70" r="12" fill="#E1452E"/>
      <rect x="84" y="92" width="20" height="18" rx="6" fill="#F2D35B"/>
      <ellipse cx="80" cy="128" rx="38" ry="9" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
  dinner: `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="80" cy="104" rx="48" ry="24" fill="#F5F1E7"/>
      <ellipse cx="80" cy="104" rx="38" ry="15" fill="#D46B2C"/>
      <path d="M56 99C66 89 78 87 92 95C104 101 110 98 118 91" stroke="#6CBE45" stroke-width="7" stroke-linecap="round"/>
      <circle cx="67" cy="102" r="5" fill="#F2D35B"/>
      <circle cx="93" cy="108" r="5" fill="#F2D35B"/>
      <ellipse cx="80" cy="130" rx="44" ry="9" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
  errands: `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="50" y="48" width="60" height="72" rx="8" fill="#1A1A1A"/>
      <rect x="57" y="55" width="46" height="58" rx="4" fill="#2F2F2F"/>
      <path d="M68 43H92" stroke="#171717" stroke-width="7" stroke-linecap="round"/>
      <circle cx="80" cy="84" r="10" fill="#F6D04D"/>
      <ellipse cx="80" cy="128" rx="36" ry="8" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
  "day out": `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="80" cy="70" r="28" fill="#1A1A1A"/>
      <circle cx="80" cy="70" r="18" fill="#F7F7F3"/>
      <path d="M52 109H108" stroke="#171717" stroke-width="7" stroke-linecap="round"/>
      <path d="M44 115L62 84" stroke="#171717" stroke-width="7" stroke-linecap="round"/>
      <path d="M116 115L98 84" stroke="#171717" stroke-width="7" stroke-linecap="round"/>
      <ellipse cx="80" cy="126" rx="42" ry="8" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
  "big spend": `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="44" y="48" width="72" height="58" rx="8" fill="#171717"/>
      <rect x="52" y="56" width="56" height="42" rx="4" fill="#2F2F2F"/>
      <rect x="60" y="66" width="40" height="12" rx="6" fill="#F5F1E7"/>
      <rect x="78" y="88" width="22" height="8" rx="4" fill="#D46B2C"/>
      <ellipse cx="80" cy="126" rx="40" ry="8" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
  "no spend": `
    <svg viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="58" y="78" width="44" height="34" rx="4" fill="#7D4F34"/>
      <path d="M55 73C59 58 68 49 80 49C92 49 101 58 105 73" stroke="#8E7A49" stroke-width="6" stroke-linecap="round"/>
      <path d="M80 78V45" stroke="#6B7E33" stroke-width="6" stroke-linecap="round"/>
      <path d="M80 52C72 46 63 48 60 58C69 61 77 59 80 52Z" fill="#6B7E33"/>
      <path d="M80 60C88 54 97 56 100 66C91 69 83 67 80 60Z" fill="#839F44"/>
      <ellipse cx="80" cy="126" rx="36" ry="8" fill="rgba(0,0,0,0.12)"/>
    </svg>
  `,
};

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

function dailyStatusMeta() {
  if (!snapshot) {
    return {
      title: "No live snapshot",
      tone: "critical",
      support: "Using your selected allowance for now.",
    };
  }

  const updatedValue = snapshot?.updated_at ?? snapshot?.last_updated;
  const updated = updatedValue ? new Date(updatedValue) : null;
  if (!updated || Number.isNaN(updated.getTime())) {
    return {
      title: "Unknown",
      tone: "neutral",
      support: "Waiting for a clean source timestamp.",
    };
  }

  const ageMs = Date.now() - updated.getTime();
  if (ageMs <= 90 * 60 * 1000) {
    return {
      title: "Live",
      tone: "positive",
      support: "You can trust this read.",
    };
  }

  if (ageMs <= 6 * 60 * 60 * 1000) {
    return {
      title: "A little old",
      tone: "caution",
      support: "Still usable, but not fresh.",
    };
  }

  return {
    title: "Stale",
    tone: "critical",
    support: "Check the portal before making a bigger call.",
  };
}

function derivedSpendingState(remaining) {
  const amount = Number(remaining || 0);
  if (amount <= 0) return "OVERDRAWN";
  if (amount < 12) return "TIGHT";
  if (amount < 25) return "WATCH IT";
  if (amount < 60) return "COMFORTABLE";
  return "PLENTY";
}

function derivedMoneyObject(remaining) {
  const amount = Number(remaining || 0);
  if (amount <= 0) return "No Spend";
  if (amount < 8) return "Coffee";
  if (amount < 18) return "Lunch";
  if (amount < 35) return "Groceries";
  if (amount < 60) return "Dinner";
  if (amount < 120) return "Errands";
  if (amount < 250) return "Day Out";
  return "Big Spend";
}

function stateClassName(label) {
  const normalized = String(label || "").toLowerCase().replace(/\s+/g, "-");
  if (normalized === "overdrawn") return "danger";
  return normalized;
}

function objectArtMarkup(label) {
  const key = String(label || "").trim().toLowerCase();
  return OBJECT_ART[key] || OBJECT_ART["dinner"];
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
  const status = dailyStatusMeta();
  const spendingState = snapshot?.spending_state ?? derivedSpendingState(remaining);
  const moneyObject = snapshot?.money_object ?? derivedMoneyObject(remaining);

  panel.classList.toggle("negative", isNegative);
  panel.classList.remove("state-plenty", "state-comfortable", "state-watch-it", "state-tight", "state-danger");
  panel.classList.add(`state-${stateClassName(spendingState)}`);
  document.getElementById("daily-number").textContent = moneyNumber(remaining);
  document.getElementById("daily-eyebrow").textContent = isNegative ? "Overspent today" : "Safe to spend";
  document.getElementById("daily-updated").textContent = `Updated ${formatUpdated(snapshot?.updated_at ?? snapshot?.last_updated)}`;
  document.getElementById("daily-object-label").textContent = moneyObject;
  document.getElementById("daily-state-label").textContent = spendingState;
  document.getElementById("daily-object-art").innerHTML = objectArtMarkup(moneyObject);

  const pill = document.getElementById("daily-status-pill");
  pill.textContent = status.title;
  pill.className = `status-pill ${status.tone}`;
}

function renderOutputPreviews() {
  const remaining = Number(snapshot?.remaining_today ?? settings.daily_allowance ?? 0);
  const isNegative = Boolean(snapshot?.is_negative ?? remaining < 0);
  const spendingState = snapshot?.spending_state ?? derivedSpendingState(remaining);
  const moneyObject = snapshot?.money_object ?? derivedMoneyObject(remaining);
  const numberText = moneyNumber(remaining);

  document.getElementById("widget-preview-number").textContent = numberText;
  document.getElementById("widget-preview-object").innerHTML = objectArtMarkup(moneyObject);
  document.getElementById("lockscreen-preview-number").textContent = numberText;
  document.getElementById("lockscreen-preview-eyebrow").textContent = isNegative ? "Overspent today" : "Safe to spend";
  document.getElementById("lockscreen-preview-object").innerHTML = objectArtMarkup(moneyObject);
  document.querySelector(".output-card-lockscreen").classList.toggle("negative", isNegative);
  document.querySelector(".output-card-widget").classList.toggle("negative", isNegative);
  document.getElementById("daily-state-label").textContent = spendingState;
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
  renderPortalOverview();
  renderSaveState();
  renderOutputPreviews();
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
  renderPortalOverview();
  renderOutputPreviews();
}

function renderPortalOverview() {
  const selected = Number(settings.daily_allowance || 55);
  const remaining = Number(snapshot?.remaining_today ?? selected);
  const resetDay = Number(settings.monthly_reset_day || 1);
  const resetTime = settings.monthly_reset_time || "04:00";
  const status = dailyStatusMeta();

  document.getElementById("overview-allowance").textContent = `$${moneyNumber(selected)}`;
  document.getElementById("overview-remaining").textContent = `$${moneyNumber(remaining)}`;
  document.getElementById("overview-exclusions").textContent = String(settings.excluded_keywords.length || 0);
  document.getElementById("overview-reset").textContent = `${resetDay} · ${resetTime}`;
  document.getElementById("overview-status").textContent = status.support;
}

function renderSaveState() {
  const node = document.getElementById("save-state");
  if (!node) return;

  if (saveState === "dirty") {
    node.textContent = "Unsaved local changes.";
    node.dataset.state = "dirty";
    return;
  }

  node.textContent = "Using saved local settings.";
  node.dataset.state = "saved";
}

function markDirty() {
  saveState = "dirty";
  renderSaveState();
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
  const raw = window.location.hash.replace(/^#\//, "") || "portal";
  const view = ["daily", "portal", "ledger"].includes(raw) ? raw : "portal";
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
    markDirty();
    renderPortal();
  });

  document.getElementById("keyword-chip-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-keyword]");
    if (!button) return;
    settings.excluded_keywords = settings.excluded_keywords.filter((item) => item !== button.dataset.keyword);
    markDirty();
    renderKeywordChips();
    renderPortalOverview();
  });

  document.getElementById("keyword-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.getElementById("keyword-input");
    const value = input.value.trim().toLowerCase();
    if (!value) return;
    if (!settings.excluded_keywords.includes(value)) {
      settings.excluded_keywords = [...settings.excluded_keywords, value];
      markDirty();
      renderKeywordChips();
      renderPortalOverview();
    }
    input.value = "";
  });

  document.getElementById("custom-allowance").addEventListener("input", markDirty);
  document.getElementById("reset-day").addEventListener("input", markDirty);
  document.getElementById("reset-time").addEventListener("input", markDirty);

  document.getElementById("save-settings").addEventListener("click", () => {
    settings.daily_allowance = Number(document.getElementById("custom-allowance").value || settings.daily_allowance || 55);
    settings.monthly_reset_day = Number(document.getElementById("reset-day").value || 1);
    settings.monthly_reset_time = document.getElementById("reset-time").value || "04:00";
    saveLocalSettings();
    saveState = "saved";
    renderPortal();
    renderDaily();
    renderPortalSnapshot();
  });

  document.getElementById("refresh-snapshot").addEventListener("click", refreshSnapshot);
}

bootstrap();
