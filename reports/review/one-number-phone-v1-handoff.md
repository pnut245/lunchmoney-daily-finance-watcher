# One Number Today Phone V1.1 Handoff

## Summary

Started the native iPhone path for One Number Today.

This branch does not create a full Xcode project yet. It adds drop-in SwiftUI files for an app target and a WidgetKit extension target, with target membership documented in `docs/PHONE_V1.md`.

## What Changed

- Added a minimal SwiftUI host app:
  - Today
  - Settings
  - Vault
- Added `OneNumberSnapshotStore` to read `budget_state.json` from an app group.
- Updated the WidgetKit provider to load the shared JSON instead of using preview-only data.
- Simplified the widget configuration intent to the one-number use case.
- Added an App Shortcut / App Intent to open One Number Today.
- Added phone target setup docs.

## App Group Contract

```text
group.com.pnut245.one-number-today
```

Shared file:

```text
budget_state.json
```

## Verification

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

Python regression tests:

```bash
.venv/bin/python -m unittest tests.test_one_number tests.test_config_validation
```

## Still Needed

- Create a real Xcode project with app and widget targets.
- Add App Group entitlements to both targets.
- Add these Swift files with correct target membership.
- Build a sync path that writes the generated `budget_state.json` into the app group container.
- Decide whether phone Settings edits should write back to Python config or remain display-only.
