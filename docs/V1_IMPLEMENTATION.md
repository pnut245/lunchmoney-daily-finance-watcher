# One Number Today V1 Implementation

## Settings

Settings live under `one_number` in `config/budget.yaml`.

Important fields:

- `daily_allowance`
- `preset_amounts`
- `excluded_categories`
- `excluded_payees`
- `reset_day`
- `reset_time`

The default daily allowance is `$55`.

The web prototype settings are browser-local only. They are useful for trying control shapes, but they do not write to `config/budget.yaml` and do not change the Python calculation. Real V1 settings persist through the `one_number` section in `config/budget.yaml`.

## Calculation

`src/one_number.py` calculates:

```text
remaining_today = daily_allowance - today_discretionary_spend
```

`today_discretionary_spend` is the sum of today’s positive, non-pending transactions after removing excluded categories and excluded payees.

## JSON State

`src/budget_state.py` writes the widget-compatible state to `data/budget_state.json` and, when installed, the lockscreen runtime copy.

Primary V1 fields:

- `daily_allowance`
- `today_discretionary_spend`
- `remaining_today`
- `is_negative`
- `last_updated`
- `excluded_categories`
- `excluded_payees`
- `reset_day`
- `reset_time`

The UI treats `remaining_today` and `is_negative` as authoritative. Legacy fields such as `safe_to_spend`, `today`, `week`, `dopamine`, `money_object`, and `spending_state` may remain for older consumers, but they must not drive the V1 visual hierarchy.

Example:

```json
{
  "daily_allowance": 55,
  "today_discretionary_spend": 18,
  "remaining_today": 37,
  "is_negative": false,
  "last_updated": "2026-06-02T23:00:00",
  "excluded_categories": ["Rent", "Utilities", "Insurance"],
  "excluded_payees": [],
  "reset_day": 1,
  "reset_time": "00:00"
}
```

## Ledger

`src/one_number.py` stores month-end rows in the SQLite table `one_number_ledger`.

Use:

```bash
python -m src.main one-number-close-month --date YYYY-MM-DD
```

The result is:

```text
daily_allowance * days_in_month - monthly_discretionary_spend
```

Ledger/Vault is secondary. It is for month-end reflection, not the daily decision.

## Lockscreen And Widget Output

`src/lockscreen.py` reads `remaining_today` and `is_negative` first.

Positive or zero:

- white background
- huge black number
- no dollar sign

Negative:

- red background
- huge white number
- no warning copy

The iPhone widget follows the same rule and renders only the number.

The tiny `SAFE TO SPEND` label can remain for now, but it must stay visually secondary to the number. It should never become a state badge or explanatory label.

## Refresh

Use:

```bash
python -m src.main one-number-state --date YYYY-MM-DD
```

The existing `run-all`, `monitor`, `alarms`, and `weekly-email` paths continue to refresh `budget_state.json` through the existing budget-state output path.

`run_lockscreen_refresh.sh` uses `.venv/bin/python` when present, otherwise it falls back to `python3` or a caller-provided `PYTHON_BIN`.

## Native Simulator Sync

The iPhone app and widget read `budget_state.json` from the App Group:

```text
group.com.pnut245.one-number-today
```

For local simulator review, generate the state and copy it into the installed simulator app group:

```bash
python -m src.main one-number-state --date YYYY-MM-DD
scripts/sync_ios_simulator_budget_state.sh
```

This preserves production behavior while proving the local path:

```text
config/budget.yaml -> calculation engine -> data/budget_state.json -> app group -> iPhone/widget render
```

## V1 Candidate Decisions

- PR #7 is the V1 candidate.
- PR #6 remains a future Poster/Object Mode exploration and should not be merged into V1.
- Web settings stay prototype-only until a safe persistence path exists.
- Legacy JSON fields stay temporarily for compatibility.
- `remaining_today` and `is_negative` are the authoritative V1 display fields.
- The next milestone is: `config/budget.yaml` -> calculation engine -> `budget_state.json` -> lockscreen/widget render.
- The core acceptance test is: can the user glance at the phone, see one number, and feel calmer?

## Safe Handoff ZIPs

Do not include local runtime/private files in review ZIPs:

- `.env`
- `.venv/`
- `data/lunchmoney.db`
- `data/*.db`
- `data/raw/`
- `node_modules/`
- `dist/`
- `build/`
- `.git/`
