# One Number Today Phone V1.1

This version starts the native iPhone path for One Number Today.

The goal is still one daily question:

```text
Can I spend this today?
```

## Included

- A minimal SwiftUI host app scaffold.
- A WidgetKit scaffold that reads `budget_state.json` from an app group.
- A shared snapshot model using the V1 JSON fields.
- An App Shortcut / App Intent to open the daily number.
- Positive state: black number on white.
- Negative state: white number on red.

## Swift Files

App target:

- `prototypes/iphone-widget/swiftui/OneNumberTodayApp.swift`
- `prototypes/iphone-widget/swiftui/OneNumberTodayView.swift`
- `prototypes/iphone-widget/swiftui/OneNumberSnapshotStore.swift`
- `prototypes/iphone-widget/swiftui/OneNumberAppIntents.swift`
- `prototypes/iphone-widget/swiftui/LunchboxWidgetModels.swift`

Widget extension target:

- `prototypes/iphone-widget/swiftui/LunchboxWidget.swift`
- `prototypes/iphone-widget/swiftui/LunchboxWidgetBundle.swift`
- `prototypes/iphone-widget/swiftui/LunchboxWidgetIntent.swift`
- `prototypes/iphone-widget/swiftui/OneNumberSnapshotStore.swift`
- `prototypes/iphone-widget/swiftui/LunchboxWidgetModels.swift`

Do not put both `OneNumberTodayApp.swift` and `LunchboxWidgetBundle.swift` in the same target. They both contain an `@main` entry point.

## App Group

The scaffold expects:

```text
group.com.pnut245.one-number-today
```

Shared file:

```text
budget_state.json
```

The app and widget should both enable the same App Group entitlement. The widget reads:

```swift
FileManager.default.containerURL(
  forSecurityApplicationGroupIdentifier: "group.com.pnut245.one-number-today"
)?.appendingPathComponent("budget_state.json")
```

## Current JSON Contract

Required fields:

```json
{
  "daily_allowance": 55,
  "today_discretionary_spend": 18,
  "remaining_today": 37,
  "is_negative": false,
  "last_updated": "2026-06-02T23:00:00"
}
```

## Still Needed For A Real App Store / TestFlight Build

- Create an Xcode iOS app target.
- Create a Widget Extension target.
- Add App Group entitlements to both targets.
- Add the Swift files above with correct target membership.
- Add a sync path that copies or downloads `budget_state.json` into the app group container.
- Decide whether the phone app edits settings directly or remains display-only while Python/config remains source of truth.

## Product Rule

The phone app and widget should not become a finance dashboard. Settings and Vault are secondary. Today is one number.
