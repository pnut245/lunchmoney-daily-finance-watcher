#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

xcrun --sdk iphoneos swiftc -target arm64-apple-ios17.0 -parse-as-library -typecheck \
  prototypes/iphone-widget/swiftui/LunchboxWidgetModels.swift \
  prototypes/iphone-widget/swiftui/OneNumberSnapshotStore.swift \
  prototypes/iphone-widget/swiftui/OneNumberTodayView.swift \
  prototypes/iphone-widget/swiftui/OneNumberAppIntents.swift \
  prototypes/iphone-widget/swiftui/OneNumberTodayApp.swift

xcrun --sdk iphoneos swiftc -target arm64-apple-ios17.0 -parse-as-library -typecheck \
  prototypes/iphone-widget/swiftui/LunchboxWidgetModels.swift \
  prototypes/iphone-widget/swiftui/OneNumberSnapshotStore.swift \
  prototypes/iphone-widget/swiftui/LunchboxWidgetIntent.swift \
  prototypes/iphone-widget/swiftui/LunchboxWidget.swift \
  prototypes/iphone-widget/swiftui/LunchboxWidgetBundle.swift

swift test
