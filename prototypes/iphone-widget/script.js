const SNAPSHOT_URL = "../../data/budget_state.json";
const STORAGE_KEY = "one-number-today-settings";
const DEFAULT_SETTINGS = {
  daily_allowance: 55,
  preset_amounts: [5, 25, 55, 111],
  excluded_categories: ["Rent", "Mortgage", "Insurance", "Utilities", "Taxes", "Transfers", "Savings", "Income"],
  excluded_payees: [],
  reset_day: 1,
  reset_time: "00:00",
};

let snapshot = null;
let settings = loadLocalSettings();

function loadLocalSettings() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    return { ...DEFAULT_SETTINGS, ...(raw || {}) };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function saveLocalSettings(next) {
  settings = { ...settings, ...next };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  renderSettings();
  renderSnapshot(snapshot);
}

async function loadSnapshot() {
  const response = await fetch(SNAPSHOT_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load snapshot: ${response.status}`);
  }
  return response.json();
}

function moneyNumber(value) {
  const number = Number(value || 0);
  return Math.round(number).toLocaleString("en-US");
}

function listText(values) {
  return (values || []).join("\n");
}

function textList(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderSnapshot(nextSnapshot) {
  if (!nextSnapshot) return;
  snapshot = nextSnapshot;
  const remaining = Number(snapshot.remaining_today ?? snapshot.meta?.remaining_today ?? 0);
  const isNegative = Boolean(snapshot.is_negative ?? remaining < 0);
  document.getElementById("app").classList.toggle("is-negative", isNegative);
  document.getElementById("app").classList.remove("is-loading");
  document.getElementById("hero-number").textContent = moneyNumber(remaining);
  document.getElementById("updated-text").textContent = `Updated ${formatUpdated(snapshot.last_updated)}`;
  renderLedger(snapshot.ledger || []);
}

function formatUpdated(value) {
  if (!value) return "unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function renderSettings() {
  const allowanceOptions = document.getElementById("allowance-options");
  const allowance = Number(settings.daily_allowance || 55);
  allowanceOptions.innerHTML = settings.preset_amounts
    .map((amount) => {
      const selected = Number(amount) === allowance;
      return `<button class="${selected ? "is-selected" : ""}" type="button" role="radio" aria-checked="${selected}" data-amount="${amount}">$${amount}</button>`;
    })
    .join("");
  document.getElementById("custom-allowance").value = allowance;
  document.getElementById("excluded-categories").value = listText(settings.excluded_categories);
  document.getElementById("excluded-payees").value = listText(settings.excluded_payees);
  document.getElementById("reset-day").value = settings.reset_day;
  document.getElementById("reset-time").value = settings.reset_time;
}

function renderLedger(entries) {
  const ledger = document.getElementById("ledger-list");
  const source = entries.length
    ? entries
    : [
        { month: "January", result: 412 },
        { month: "February", result: 689 },
        { month: "March", result: -82 },
        { month: "April", result: 515 },
      ];
  ledger.innerHTML = source
    .map((entry) => {
      const result = Number(entry.result || 0);
      const signed = `${result >= 0 ? "+" : "-"}${Math.abs(Math.round(result)).toLocaleString("en-US")}`;
      return `<div class="ledger-row"><span>${entry.month}</span><strong>${signed}</strong></div>`;
    })
    .join("");
}

function showScreen(name) {
  document.querySelectorAll("[data-screen-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.screenPanel !== name;
  });
  document.querySelectorAll("[data-screen]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.screen === name);
  });
}

async function refresh() {
  try {
    if (new URLSearchParams(window.location.search).get("demo") === "negative") {
      renderSnapshot({
        daily_allowance: 55,
        today_discretionary_spend: 67,
        remaining_today: -12,
        is_negative: true,
        last_updated: "2026-06-02T23:00:00",
        ledger: [],
      });
      return;
    }
    renderSnapshot(await loadSnapshot());
  } catch (error) {
    document.getElementById("updated-text").textContent = "Snapshot unavailable";
    document.getElementById("hero-number").textContent = moneyNumber(settings.daily_allowance);
    renderLedger([]);
  }
}

document.querySelectorAll("[data-screen]").forEach((button) => {
  button.addEventListener("click", () => showScreen(button.dataset.screen));
});

document.getElementById("allowance-options").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-amount]");
  if (button) saveLocalSettings({ daily_allowance: Number(button.dataset.amount) });
});

document.getElementById("save-settings").addEventListener("click", () => {
  saveLocalSettings({
    daily_allowance: Number(document.getElementById("custom-allowance").value || 55),
    excluded_categories: textList(document.getElementById("excluded-categories").value),
    excluded_payees: textList(document.getElementById("excluded-payees").value),
    reset_day: Number(document.getElementById("reset-day").value || 1),
    reset_time: document.getElementById("reset-time").value || "00:00",
  });
});

document.getElementById("reload-button").addEventListener("click", refresh);

renderSettings();
refresh();
