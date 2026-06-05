aqwesome# iPhone Widget Prototype

This folder contains the current browser prototype for the two-experience model:

- `#/daily` for the minimal daily number
- `#/portal` for planning, settings, and projections
- `#/ledger` for buried monthly history

## Local browser prototype

Serve the repo root and open the prototype page:

```bash
cd /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher
python3 -m http.server 8421
```

Then visit:

```text
http://localhost:8421/prototypes/iphone-widget/
```

The page reads live data from:

- `/data/widget_snapshot.json`
- `/data/settings.json`
- `/data/ledger.json`

The prototype auto-refreshes the daily snapshot every minute so you can leave it open while the local producer updates the snapshot on its own cadence.

## Native scaffold

`swiftui/` contains the earlier WidgetKit/App Intents scaffold that informed the native prototype.

The active native app + widget implementation now lives under:

- `/ios/Syzygy/`
- `/ios/OneNumberWidget/`
- `/ios/Shared/`
- `/Syzygy.xcodeproj`
