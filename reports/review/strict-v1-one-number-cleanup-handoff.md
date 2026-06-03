# Strict V1 One Number Cleanup Handoff

## Summary

Tightened One Number Today around the core product sentence:

```text
If I focus on this one number today, I can ignore everything else.
```

The lockscreen, web daily screen, iPhone app, and widget now treat `remaining_today` and `is_negative` as the primary display fields. Positive or zero stays black on white. Negative is white on red. The hero number has no dollar sign.

## Files Changed

- `src/lockscreen.py`
- `src/budget_state.py`
- `run_lockscreen_refresh.sh`
- `prototypes/iphone-widget/index.html`
- `prototypes/iphone-widget/script.js`
- `prototypes/iphone-widget/styles.css`
- `prototypes/iphone-widget/swiftui/OneNumberTodayView.swift`
- `docs/DESIGN.md`
- `docs/V1_IMPLEMENTATION.md`
- `README.md`
- `tests/test_lockscreen_v1.py`

## Setup / Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest tests.test_one_number tests.test_config_validation tests.test_lockscreen_v1
scripts/verify_phone_swift.sh
```

Web prototype:

```bash
python3 -m http.server 8423
open http://127.0.0.1:8423/prototypes/iphone-widget/
```

Lockscreen render:

```bash
python -m src.lockscreen data/budget_state.json data/lockscreen_latest.png
```

`run_lockscreen_refresh.sh` now uses `.venv/bin/python` when present, otherwise `python3` or `PYTHON_BIN`.

## Review Images

- Positive lockscreen: `reports/review/one-number-v1-lockscreen-positive.png`
- Negative lockscreen: `reports/review/one-number-v1-lockscreen-negative.png`
- Web daily: `reports/review/one-number-v1-web-daily.png`
- Web negative: `reports/review/one-number-v1-web-negative.png`
- Web settings: `reports/review/one-number-v1-web-settings.png`
- iPhone simulator: `reports/review/one-number-v1-ios-simulator.jpg`

## Current JSON Contract

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

## Known Issues / Tradeoffs

- The web Settings controls are prototype-only and save to browser `localStorage`; real calculation settings still come from `config/budget.yaml`.
- Legacy JSON fields such as `safe_to_spend`, `week`, `dopamine`, `money_object`, and `spending_state` may still exist for compatibility, but V1 renderers ignore them when `remaining_today` is present.
- The old generic JSON lockscreen renderer remains as a fallback only when V1 fields are absent.

## Decisions For V1 Candidate

- Keep the tiny `SAFE TO SPEND` label for now, but keep it visually secondary to the number.
- Do not wire web settings to `config/budget.yaml` yet unless a safe persistence path exists.
- Keep legacy JSON fields temporarily for compatibility.
- Treat `remaining_today` and `is_negative` as authoritative V1 display fields.
- Do not merge PR #6 into V1. Preserve it as future Poster/Object Mode exploration.

## Next Milestone

```text
config/budget.yaml -> calculation engine -> budget_state.json -> lockscreen/widget render
```

## Acceptance Test

Can the user glance at the phone, see one number, and feel calmer?

## Product Questions

- Should web settings write back to `config/budget.yaml`, or remain a prototype surface until a native settings flow exists?
- Should legacy top-level fields be removed completely after downstream consumers move to `remaining_today`?
