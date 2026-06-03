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

Legacy fields such as `safe_to_spend` remain for existing prototype consumers, but now point at the V1 remaining number.

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

## Refresh

Use:

```bash
python -m src.main one-number-state --date YYYY-MM-DD
```

The existing `run-all`, `monitor`, `alarms`, and `weekly-email` paths continue to refresh `budget_state.json` through the existing budget-state output path.
