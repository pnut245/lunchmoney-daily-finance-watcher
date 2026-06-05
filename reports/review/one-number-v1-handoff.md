# One Number Today V1 Review Handoff

## Summary

Refactored the current Lunch Money watcher toward a V1 of One Number Today. The existing Lunch Money pull/check/report pipeline and `data/budget_state.json` output path are preserved. A new V1 layer now calculates one daily remaining amount and exposes widget-compatible JSON fields.

The daily prototype is no longer a dashboard. It has three primary screens:

- Today: one oversized number.
- Settings: daily allowance, exclusions, and monthly reset controls.
- Vault: month-end results only.

## Files Changed

- `config/budget.yaml`
- `src/one_number.py`
- `src/budget_state.py`
- `src/main.py`
- `src/storage.py`
- `prototypes/iphone-widget/index.html`
- `prototypes/iphone-widget/script.js`
- `prototypes/iphone-widget/styles.css`
- `prototypes/iphone-widget/swiftui/SyzygyWidget.swift`
- `prototypes/iphone-widget/swiftui/SyzygyWidgetModels.swift`
- `tests/test_one_number.py`
- `docs/PRODUCT.md`
- `docs/DESIGN.md`
- `docs/V1_IMPLEMENTATION.md`
- `README.md`

Existing local changes unrelated to this V1 were already present in `install-lockscreen-launch-agent.sh`, `run_lockscreen_refresh.sh`, `src/wallpaper.py`, and `tests/test_lockscreen_background.py`.

## Setup / Run

Generate widget-compatible JSON from local cache:

```bash
.venv/bin/python -m src.main one-number-state --date 2026-06-02
```

Serve the web prototype:

```bash
python3 -m http.server 8422
```

Open:

```text
http://localhost:8422/prototypes/iphone-widget/
```

Negative demo preview:

```text
http://localhost:8422/prototypes/iphone-widget/?demo=negative
```

Store a month-end ledger entry:

```bash
.venv/bin/python -m src.main one-number-close-month --date 2026-06-30
```

## Screenshots

- Positive daily number: `reports/review/one-number-positive.png`
- Negative daily number: `reports/review/one-number-negative.png`
- Settings: `reports/review/one-number-settings.png`
- Vault: `reports/review/one-number-vault.png`

## Current JSON Shape

```json
{
  "daily_allowance": 55.0,
  "today_discretionary_spend": 0.0,
  "remaining_today": 55.0,
  "is_negative": false,
  "last_updated": "2026-06-03T06:31:55.783246+00:00",
  "excluded_categories": [
    "Rent",
    "Mortgage",
    "Insurance",
    "Utilities",
    "Taxes",
    "Transfers",
    "Savings",
    "Income"
  ],
  "excluded_payees": [],
  "reset_day": 1,
  "reset_time": "00:00"
}
```

Legacy fields such as `safe_to_spend` remain for existing consumers, but now point at the V1 remaining number.

## Verification

```bash
.venv/bin/python -m unittest tests.test_one_number tests.test_config_validation tests.test_lockscreen_background
```

Result: 18 tests passed.

Browser verification:

- Today screen shows one dominant `55`.
- Positive state is black on white.
- Negative demo shows `-12`, white on red.
- Settings exposes `$5`, `$25`, `$55`, `$111`, custom allowance, exclusions, reset day, and reset time.
- Vault shows month-end rows only.

## Known Issues / Tradeoffs

- The web Settings prototype persists edits in browser `localStorage`; the backend source of truth remains `config/budget.yaml`.
- Month-end reset is implemented as a command that stores ledger rows; automatic scheduled reset wiring is not enabled yet.
- The local data cache for `2026-06-02` had no same-day transactions, so the current generated state remains `$55`.
- The iPhone WidgetKit scaffold still uses preview data and does not yet read the shared JSON file from an installed app container.

## Review Question

Does the daily experience show one number clearly enough that the user feels calmer, not more tempted to inspect details?
