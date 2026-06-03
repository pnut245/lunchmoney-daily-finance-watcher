# One Number Today Phone V1.1 Handoff

## Summary

Started the native iPhone path for One Number Today.

This branch now includes a generated Xcode project for a real iOS app target and WidgetKit extension target. `project.yml` is the reviewable source of truth for target membership, entitlements, and generated Info.plists.

## What Changed

- Added a minimal SwiftUI host app:
  - Today
  - Settings
  - Vault
- Added `OneNumberSnapshotStore` to read `budget_state.json` from an app group.
- Updated the WidgetKit provider to load the shared JSON instead of using preview-only data.
- Simplified the widget configuration intent to the one-number use case.
- Added an App Shortcut / App Intent to open One Number Today.
- Added a Swift Package build harness and snapshot tests.
- Added phone target setup docs.
- Added `project.yml` for XcodeGen.
- Generated `OneNumberToday.xcodeproj`.
- Generated app and widget Info.plists and App Group entitlement files.
- Verified the app builds, installs, and launches on an iPhone 17 simulator.

## App Group Contract

```text
group.com.pnut245.one-number-today
```

Shared file:

```text
budget_state.json
```

## Verification

Full verification:

```bash
scripts/verify_phone_swift.sh
```

Swift type checks:

```bash
xcrun --sdk iphoneos swiftc -target arm64-apple-ios17.0 -parse-as-library -typecheck \
  prototypes/iphone-widget/swiftui/LunchboxWidgetModels.swift \
  prototypes/iphone-widget/swiftui/OneNumberSnapshotStore.swift \
  prototypes/iphone-widget/swiftui/OneNumberTodayView.swift \
  prototypes/iphone-widget/swiftui/OneNumberAppIntents.swift \
  prototypes/iphone-widget/swiftui/OneNumberTodayApp.swift
```

```bash
xcrun --sdk iphoneos swiftc -target arm64-apple-ios17.0 -parse-as-library -typecheck \
  prototypes/iphone-widget/swiftui/LunchboxWidgetModels.swift \
  prototypes/iphone-widget/swiftui/OneNumberSnapshotStore.swift \
  prototypes/iphone-widget/swiftui/LunchboxWidgetIntent.swift \
  prototypes/iphone-widget/swiftui/LunchboxWidget.swift \
  prototypes/iphone-widget/swiftui/LunchboxWidgetBundle.swift
```

Both passed.

Swift Package tests:

- `decodesOneNumberSnapshot`
- `negativeSnapshotDisplaysSignedNumber`

Both passed.

Generated Xcode project:

```bash
xcodegen generate
```

Simulator build/run:

- Scheme: `OneNumberToday`
- Simulator: `iPhone 17`
- Bundle ID: `com.pnut245.OneNumberToday`
- Result: build, install, and launch passed.

Simulator screenshot:

```text
reports/review/one-number-ios-simulator.jpg
```

Python regression tests:

```bash
.venv/bin/python -m unittest tests.test_one_number tests.test_config_validation
```

## Still Needed

- Set the Apple development team for signing.
- Create/enable the App Group in the Apple developer account.
- Build a sync path that writes the generated `budget_state.json` into the app group container.
- Decide whether phone Settings edits should write back to Python config or remain display-only.
