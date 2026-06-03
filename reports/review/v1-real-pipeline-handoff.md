# One Number Today Real Pipeline Handoff

## Summary

PR #7 was squash-merged into `main` as:

```text
5decd91 Strict V1 One Number cleanup
```

This branch starts the next milestone:

```text
config/budget.yaml -> calculation engine -> data/budget_state.json -> lockscreen/widget render
```

The existing calculation path already reads `one_number` settings from `config/budget.yaml`, calculates `today_discretionary_spend`, writes `data/budget_state.json`, and renders the strict V1 lockscreen from that JSON. This branch adds regression coverage for that pipeline and a simulator sync script so the iPhone/widget prototype can consume the generated JSON through its App Group.

## Files Changed

- `tests/test_v1_pipeline.py`
- `scripts/sync_ios_simulator_budget_state.sh`
- `docs/V1_IMPLEMENTATION.md`
- `reports/review/v1-real-pipeline-handoff.md`
- `reports/review/v1-pipeline-lockscreen-positive.png`
- `reports/review/v1-pipeline-lockscreen-negative.png`
- `reports/review/v1-pipeline-web-daily.png`
- `reports/review/v1-pipeline-web-settings.png`
- `reports/review/v1-pipeline-web-negative.png`
- `reports/review/v1-pipeline-ios-simulator.jpg`

## Setup / Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest tests.test_one_number tests.test_config_validation tests.test_lockscreen_v1 tests.test_v1_pipeline
scripts/verify_phone_swift.sh
```

Generate state and lockscreen:

```bash
.venv/bin/python -m src.main one-number-state --date 2026-06-03
.venv/bin/python -m src.lockscreen data/budget_state.json data/lockscreen_latest.png
```

Serve web prototype:

```bash
python3 -m http.server 8423
open http://127.0.0.1:8423/prototypes/iphone-widget/
```

Sync generated JSON into the iOS simulator App Group after the app is installed:

```bash
scripts/sync_ios_simulator_budget_state.sh
```

## Example Config

```yaml
one_number:
  enabled: true
  daily_allowance: 55.00
  preset_amounts:
    - 5
    - 25
    - 55
    - 111
  excluded_categories:
    - Rent
    - Mortgage
    - Insurance
    - Utilities
    - Taxes
    - Transfers
    - Savings
    - Income
  excluded_payees: []
  reset_day: 1
  reset_time: "00:00"
```

## Example Budget State

Generated from local sample cache with one included `$18` restaurant transaction plus excluded transfer/utility rows:

```json
{
  "daily_allowance": 55.0,
  "today_discretionary_spend": 18.0,
  "remaining_today": 37.0,
  "is_negative": false,
  "last_updated": "2026-06-03T08:13:05.001095+00:00",
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

Legacy fields may also be present for compatibility, but V1 renderers prioritize `remaining_today` and `is_negative`.

## Review Images

- Positive lockscreen from generated JSON: `reports/review/v1-pipeline-lockscreen-positive.png`
- Negative lockscreen sample: `reports/review/v1-pipeline-lockscreen-negative.png`
- Web daily from generated JSON: `reports/review/v1-pipeline-web-daily.png`
- Web settings: `reports/review/v1-pipeline-web-settings.png`
- Web negative sample: `reports/review/v1-pipeline-web-negative.png`
- iPhone simulator after App Group sync: `reports/review/v1-pipeline-ios-simulator.jpg`

## Verification

- PR #7 merged into `main`.
- Python suite passed: 13 tests.
- Swift phone/widget verification passed.
- CLI generated `data/budget_state.json`.
- CLI rendered `data/lockscreen_latest.png`.
- Web daily rendered `37` from generated `data/budget_state.json`.
- iPhone simulator rendered `37` after syncing `data/budget_state.json` into the App Group.
- Positive state remained black on white with no dollar sign.
- Negative state remained white on red with no warning label.

## Settings Status

Web settings remain prototype-only. They do not write to `config/budget.yaml`.

Real calculation settings continue to come from `config/budget.yaml`.

## Known Issues / Tradeoffs

- The simulator App Group sync is manual for now via `scripts/sync_ios_simulator_budget_state.sh`.
- The production phone sync path is still not built.
- Legacy fields remain in `budget_state.json` for compatibility even though V1 renderers ignore them.
- Local sample `data/lunchmoney.db`, `data/budget_state.json`, and `data/lockscreen_latest.png` are intentionally ignored and not committed.

## Product Questions

- Should the simulator sync script become part of a larger local preview command?
- What should own production phone sync: local Mac process, API pull from app, iCloud/app group bridge, or a small backend?
- When all consumers move to `remaining_today`, should legacy fields be removed from `budget_state.json`?

## Acceptance Question

Does the daily experience show one number clearly enough that the user feels calmer, not more tempted to inspect details?
