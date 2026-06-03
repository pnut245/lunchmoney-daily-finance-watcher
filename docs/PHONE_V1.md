# One Number Today Phone V1.1

This version starts the native iPhone path for One Number Today.

The goal is still one daily question:

```text
Can I spend this today?
```

## Included

- A minimal SwiftUI host app scaffold.
- A WidgetKit scaffold that reads `budget_state.json` from an app group.
- A generated Xcode project with app and widget targets.
- An XcodeGen project spec so target membership stays reviewable.
- A shared snapshot model using the V1 JSON fields.
- An App Shortcut / App Intent to open the daily number.
- A Swift Package build harness for the shared phone code.
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
  "today_discretionary_spend": 0,
  "remaining_today": 55,
  "is_negative": false,
  "last_updated": "2026-06-02T23:00:00"
}
```

## Xcode Project

The generated project is:

```text
OneNumberToday.xcodeproj
```

The project source of truth is:

```text
project.yml
```

Regenerate after target changes:

```bash
xcodegen generate
```

## Still Needed For A Real App Store / TestFlight Build

- Set the Apple development team for signing.
- Create/enable the App Group in the Apple developer account.
- Add a sync path that copies or downloads `budget_state.json` into the app group container.
- Decide whether the phone app edits settings directly or remains display-only while Python/config remains source of truth.

## Verification

Run:

```bash
scripts/verify_phone_swift.sh
```

This checks:

- iPhone app target Swift files with the iPhone SDK.
- Widget extension Swift files with the iPhone SDK.
- Swift Package tests for snapshot decoding/display formatting.

Simulator verification also passed with the generated Xcode project on iPhone 17.

## Product Rule

The phone app and widget should not become a finance dashboard. Settings and Vault are secondary. Today is one number.
