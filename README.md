# Lunch Money Daily Finance Watcher

A local-first starter project for pulling read-only data from the Lunch Money API, storing SQLite/raw JSON snapshots, running anomaly/rule checks, and producing a daily markdown report for deeper ChatGPT review.

GitHub repo: [pnut245/lunchmoney-daily-finance-watcher](https://github.com/pnut245/lunchmoney-daily-finance-watcher)

## One Number Today V1

This repo now includes a V1 layer for **One Number Today**: an ADHD-friendly daily allowance interface centered on one number.

Core docs:

- `docs/PRODUCT.md`
- `docs/DESIGN.md`
- `docs/V1_IMPLEMENTATION.md`

Generate the widget-compatible JSON state:

```bash
python -m src.main one-number-state --date 2026-06-02
```

Serve the prototype from the repo root and open:

```text
http://localhost:8421/prototypes/iphone-widget/
```

## Native iPhone Prototype

The repo now includes a native SwiftUI app plus WidgetKit extension under `ios/` and a generated Xcode project:

- `Lunchbox.xcodeproj`
- `ios/Lunchbox/`
- `ios/OneNumberWidget/`
- `ios/Shared/`

Regenerate the Xcode project after source-controlled project changes:

```bash
xcodegen generate
```

Run the local snapshot server first so the app and widget can fetch live data:

```bash
cd /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher
python3 -m http.server 8422
```

Then open `Lunchbox.xcodeproj` in Xcode and run the `Lunchbox` scheme on an iPhone simulator.
The default in-app snapshot URL is:

```text
http://127.0.0.1:8422/data/widget_snapshot.json
```

For a real iPhone on the same network, replace `127.0.0.1` with this Mac's LAN IP.

To refresh the baked-in suggested LAN URL after your Mac's IP changes:

```bash
./update-ios-dev-host.sh
```

The app now declares local network usage and local ATS intent for private-network HTTP testing. On a real iPhone, expect a Local Network permission prompt the first time the app tries to reach your Mac.

For Personal Team installs, the current native prototype avoids `App Groups` so signing is simpler. The app and widget do not share edited URL settings yet; the widget uses its own built-in default URL and the app stores its URL locally.

This project uses Lunch Money API v2 by default because Lunch Money recommends new projects start there, while v1 remains public beta. v2 is still alpha, so all API calls are isolated in `src/lunchmoney_client.py`.

Docs:

- v2 docs: https://alpha.lunchmoney.dev/
- v2 API reference: https://alpha.lunchmoney.dev/v2/docs
- legacy v1 docs: https://lunchmoney.dev/

## What It Does

- Pulls transactions, categories, manual accounts, Plaid accounts, recurring items, budget settings, and budget summary when available.
- Saves raw JSON snapshots under `data/raw/YYYY-MM-DD/`.
- Stores normalized tables in `data/lunchmoney.db`.
- Runs starter rule checks for high transactions, new merchants, possible duplicates, uncategorized transactions, recurring amount changes, unusual daily spend, and budget pacing when budget data is available.
- Writes daily reports to `reports/daily/YYYY-MM-DD.md`.
- Copies the newest daily report to `reports/latest.md`.
- Includes a "Needs ChatGPT Review" section with structured JSON context.
- Builds on-demand finance question packets for ChatGPT/Codex review.
- Leaves optional alarm, weekly email, Slack, and local budget overlay helpers in place for later use.

Read-only only: the code only uses `GET` endpoints. There are no write/update/delete API calls.

## Quick Start

```bash
cd /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LUNCHMONEY_ACCESS_TOKEN=...
python -m src.main run-all
```

Expected outputs:

- `data/lunchmoney.db`
- `data/raw/YYYY-MM-DD/*.json`
- `reports/daily/YYYY-MM-DD.md`
- `reports/latest.md`

## CLI

```bash
python -m src.main pull
python -m src.main check
python -m src.main report
python -m src.main run-all
python -m src.main alarms
python -m src.main monitor
python -m src.main weekly-email
python -m src.main ask 'Can I afford a $50 purchase this week?'
python -m src.main merchant-summary 'Trader Joe' --days 30
python -m src.main impact 50 --merchant 'Whole Foods'
python -m src.lockscreen data/budget_state.json data/lockscreen_latest.png
```

Useful options:

```bash
python -m src.main pull --start-date 2026-01-01 --end-date 2026-05-30
python -m src.main check --date 2026-05-30
python -m src.main report --date 2026-05-30
python -m src.main sample-report
python -m src.main sample-alarms
python -m src.main sample-weekly-email
python -m src.main weekly-email --send
python -m src.main weekly-email --slack
python -m src.main merchant-summary 'OpenAI' --days 30
python -m src.main impact 25 --category Coffee
```

`sample-report` uses mocked data and does not touch `data/lunchmoney.db`.

The main daily workflow is `run-all`. The `alarms`, `monitor`, `ask`, and `weekly-email` commands are optional helpers for later budget-review workflows.

## Lockscreen Overlay

The repo includes a small lockscreen renderer that converts a local JSON budget snapshot into a PNG:

```bash
python -m src.lockscreen data/budget_state.json data/lockscreen_latest.png
```

To render and apply the generated image as the current macOS desktop wallpaper:

```bash
./run_lockscreen_refresh.sh
```

Expected default paths:

- `data/budget_state.json`
- `data/lockscreen_latest.png`

The renderer accepts flexible JSON. It works best with fields like:

```json
{
  "title": "Sunday Budget Brief",
  "summary": "On track overall. Dining is running hot.",
  "updated_at": "2026-06-01T06:45:00Z",
  "metrics": [
    {"label": "Cash", "value": "$12,450"},
    {"label": "MTD Spend", "value": "$2,140"},
    {"label": "Review Items", "value": "3"}
  ],
  "notes": [
    "Check two large grocery runs",
    "Decide whether Coffee limit should increase"
  ]
}
```

If those fields are absent, it falls back to rendering a simple key/value dump of the JSON.

For the stripped-down ADHD lockscreen, provide these fields instead:

```json
{
  "safe_to_spend": "$42",
  "spending_state": "COMFORTABLE",
  "money_object": "Dinner Plate",
  "today": "$42",
  "week": "$210",
  "dopamine": "$35"
}
```

When those fields are present, the renderer switches to the minimal layout automatically and uses the lockscreen V1 direction:

- one dominant safe-to-spend number
- one object label that gives the number meaning
- one urgency color/theme based on the spending state
- Week and Dopamine as supporting context only

The current spending-state ladder is:

- `PLENTY`
- `COMFORTABLE`
- `WATCH IT`
- `TIGHT`
- `DANGER`
- `OVERDRAWN`

The watcher now writes this snapshot automatically after `monitor`, `alarms`, `run-all`, and `weekly-email`. By default it updates:

- `data/budget_state.json`
- `data/widget_snapshot.json`
- `data/lockscreen_latest.png`
- `~/Library/Application Support/ief-lockscreen/budget_state.json` if the LaunchAgent runtime exists
- `~/Library/Application Support/ief-lockscreen/widget_snapshot.json` if the LaunchAgent runtime exists
- `~/Library/Application Support/ief-lockscreen/lockscreen_latest.png` if the LaunchAgent runtime exists
- `~/Library/Application Support/lunchmoney-finance-watcher/widget_snapshot.json` if the hourly monitor runtime exists

`run_lockscreen_refresh.sh` renders the PNG and, by default, applies it as the current macOS wallpaper with `osascript`. To render without changing the wallpaper:

```bash
LOCKSCREEN_APPLY_WALLPAPER=0 ./run_lockscreen_refresh.sh
```

The lockscreen amounts are derived from the local discretionary budget policy in `config/budget.yaml`:

- `safe_to_spend` / `today`: remaining discretionary budget spread across the remaining days in the month
- `week`: a tighter 5-day projection from that same remaining budget
- `dopamine`: a stricter sub-cap based on `dopamine_ratio_of_today` and `dopamine_daily_cap`

The watcher also derives:

- `spending_state`: urgency bucket based on safe-to-spend, alarms, and cash-buffer pressure
- `money_object`: a simple purchase metaphor such as `Coffee Cup`, `Grocery Bag`, or `Shopping Cart`

You can tune the behavior under the `lockscreen:` section in `config/budget.yaml`.

### LaunchAgent

Install the local LaunchAgent to regenerate the PNG every 15 minutes:

```bash
./install-lockscreen-launch-agent.sh
```

This installs `com.ief.lockscreen.refresh.plist` into `~/Library/LaunchAgents`, runs at load plus every 15 minutes, and writes logs to `~/Library/Logs/ief-lockscreen/`.
The installer also copies a self-contained runtime into `~/Library/Application Support/ief-lockscreen/` so the agent does not depend on macOS background access to `Documents`, then applies the refreshed wallpaper on each scheduled run.

### Hourly Monitor LaunchAgent

Install the local LaunchAgent to run the read-only hourly finance monitor outside Codex:

```bash
./install-hourly-monitor-launch-agent.sh
```

This installs `com.ief.lunchmoney.hourly-monitor.plist` into `~/Library/LaunchAgents`, runs at load plus every hour, and writes logs to `~/Library/Logs/lunchmoney-finance-watcher/`.
The installer also copies a self-contained runtime into `~/Library/Application Support/lunchmoney-finance-watcher/` so the agent does not depend on macOS background access to `Documents`.

Runtime artifacts land under:

- `~/Library/Application Support/lunchmoney-finance-watcher/reports/`
- `~/Library/Application Support/lunchmoney-finance-watcher/data/`

Useful checks:

```bash
launchctl list | rg com.ief.lunchmoney.hourly-monitor
tail -n 40 ~/Library/Logs/lunchmoney-finance-watcher/hourly-monitor.out.log
tail -n 40 ~/Library/Logs/lunchmoney-finance-watcher/hourly-monitor.err.log
```

If you switch to this local agent, disable the Codex automation for the same watcher so it stops generating Playground-area inbox items.

## Local Merchant Map

`config/merchant_map.yaml` contains local-only suggestions like:

```yaml
merchant_map:
  - match: "OpenAI"
    category: "Software / AI Tools"
    confidence: high
    alert_policy: review_recurring
```

These rules do not write categories back to Lunch Money. They only help local reports suggest categories and review policies.

## Finance Question Mode

Use `ask` when Patrick has a finance-related question and wants a local context packet for ChatGPT/Codex:

```bash
python -m src.main ask 'Can I afford a $50 purchase this week?'
python -m src.main ask 'What should count as an urgent finance alert?'
python -m src.main ask 'Is this OpenAI duplicate charge real?'
```

Outputs:

- `reports/questions/YYYYMMDDTHHMMSSZ.md`
- `reports/questions/latest.md`

The packet includes a cautious draft answer, recent spend summary, active rule hits, top payees, category spend, local merchant-map suggestions, account summary, current criteria, and structured JSON context. It does not call an LLM by itself yet.

Use `merchant-summary` for quick merchant/payee rollups:

```bash
python -m src.main merchant-summary 'Trader Joe' --days 30
```

Outputs:

- `reports/merchants/YYYY-MM-DD-merchant-30d.md`
- `reports/merchants/latest.md`

Use `impact` for fast purchase checks:

```bash
python -m src.main impact 50 --merchant 'Whole Foods'
python -m src.main impact 25 --category Coffee
```

Outputs:

- `reports/impact/YYYYMMDDTHHMMSSZ.md`
- `reports/impact/latest.md`

The impact calculator uses local suggested category spend, configured monthly limits, discretionary limits, and visible cash balance. It is intended for quick guidance, not professional financial advice.

Limitations:

- This is not professional financial advice.
- Cash buffer, monthly savings target, discretionary categories, and ignored merchants still need Patrick's real criteria.
- Answers are only as good as the local Lunch Money cache and configured rules.

## Configuration

Edit:

- `config/rules.yaml` for anomaly rules.
- `config/budget.yaml` for local budget limits, alarm promotion, resources, and weekly email settings.
- `config/merchant_map.yaml` for local-only merchant category suggestions.

Starter TODOs intentionally left open:

- define Patrick's actual alert thresholds
- define categories considered discretionary
- define merchants to ignore
- define target monthly savings / cash buffer
- enable gated OpenAI API automation only after privacy and alert criteria are stable
- later build Streamlit dashboard

## OpenAI API Automation Decision

Decision: approved later, gated, and disabled by default.

The watcher should keep using local context packets first. OpenAI API calls should only be added after Patrick's alert criteria, privacy boundaries, and review flows are stable.

Allowed first use cases:

- summarize `reports/questions/latest.md` on demand
- summarize `reports/alarms/latest.md` when alarms are active
- classify alerts as interrupt, weekly-review, or dashboard-only
- suggest merchant-map edits for Patrick review

Boundaries:

- do not send raw full transaction dumps by default
- do not send tokens, credentials, or account identifiers
- do not let the model write categories back to Lunch Money
- do not post private financial details to Slack without Patrick approval
- answers should cite local report paths and state uncertainty

## Environment Variables

Required:

```bash
export LUNCHMONEY_ACCESS_TOKEN=...
```

Optional:

```bash
export LUNCHMONEY_API_BASE_URL=https://api.lunchmoney.dev/v2
```

You can point `LUNCHMONEY_API_BASE_URL` at Lunch Money's v2 mock server while experimenting.

Optional weekly email sending for the later Sunday budget workflow:

```bash
export BUDGET_EMAIL_TO=you@example.com
export BUDGET_EMAIL_FROM=you@example.com
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USERNAME=you@example.com
export SMTP_PASSWORD=...
export SMTP_USE_TLS=true
python -m src.main weekly-email --send
```

Without `--send`, the weekly email is just written locally as markdown.

Optional Slack completion notice:

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
python -m src.main weekly-email --slack
```

The Slack message is intentionally short: it only says the Sunday budget brief is ready, how many review items were found, and where the local markdown files were written. It does not include transaction details unless you change `config/budget.yaml`.

## Scheduling With Cron

Mac/Linux example, every day at 8:30 AM:

First create a local env file outside git, for example `~/.lunchmoney-watcher.env`:

```bash
export LUNCHMONEY_ACCESS_TOKEN=...
```

```cron
30 8 * * * cd /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher && /usr/bin/env bash -lc 'source ~/.lunchmoney-watcher.env && source .venv/bin/activate && python -m src.main run-all' >> /tmp/lunchmoney-daily-finance-watcher.log 2>&1
```

The daily report will be written to `reports/daily/YYYY-MM-DD.md` and copied to `reports/latest.md`.

Optional Sunday budget email cron, if SMTP/Slack are configured later:

```cron
0 9 * * 0 cd /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher && /usr/bin/env bash -lc 'source ~/.lunchmoney-watcher.env && source .venv/bin/activate && python -m src.main weekly-email --send --slack' >> /tmp/lunchmoney-budget-watcher.log 2>&1
```

## Privacy Notes

The generated database, raw snapshots, and reports can contain personal financial data. `.gitignore` excludes generated financial outputs by default. Keep this repo local or private unless you intentionally scrub or encrypt outputs.

## Project Layout

```text
config/rules.yaml          Rule thresholds and TODOs
config/budget.yaml         Local budget limits, review policy, weekly email settings
config/merchant_map.yaml   Local-only merchant category suggestions
data/schema.md             Human-readable SQLite schema notes
data/lunchmoney.db         Generated local database
data/raw/YYYY-MM-DD/       Generated raw API snapshots
reports/alarms/latest.md   Generated newest alarm report
reports/weekly/latest.md   Generated newest weekly email draft
reports/daily/YYYY-MM-DD.md Generated daily finance watcher report
reports/latest.md          Generated newest daily report
src/lunchmoney_client.py   Isolated Lunch Money v2 API wrapper
src/storage.py             SQLite schema and persistence
src/rules.py               Rule/anomaly checks
src/alarms.py              Alarm promotion and local budget triggers
src/weekly_email.py        Weekly email draft and optional SMTP sending
src/slack_notify.py        Optional Slack webhook completion notice
src/report.py              Markdown report builder
src/main.py                CLI
```

## Optional GitHub Actions

An opt-in workflow template lives at `.github/workflows/lunchmoney-daily.yml.disabled`. It will not run unless you rename it to `.yml`, add the `LUNCHMONEY_ACCESS_TOKEN` repository secret, and accept the privacy tradeoff of running this outside your local machine.
