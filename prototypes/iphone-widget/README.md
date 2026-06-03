aqwesome# iPhone Widget Prototype

This folder contains a working local prototype for an iPhone finance widget and a parallel SwiftUI scaffold for a future native WidgetKit build.

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

The prototype auto-refreshes every minute so you can leave it open while the local producer updates the snapshot on its own cadence.

## Native scaffold

`swiftui/` contains the earlier WidgetKit/App Intents scaffold that informed the native prototype.

The active native app + widget implementation now lives under:

- `/ios/Lunchbox/`
- `/ios/OneNumberWidget/`
- `/ios/Shared/`
- `/Lunchbox.xcodeproj`
