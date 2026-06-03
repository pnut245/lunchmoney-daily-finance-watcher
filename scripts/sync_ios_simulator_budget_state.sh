#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

SIMULATOR_ID="${SIMULATOR_ID:-booted}"
BUNDLE_ID="${BUNDLE_ID:-com.pnut245.OneNumberToday}"
APP_GROUP_ID="${APP_GROUP_ID:-group.com.pnut245.one-number-today}"
SOURCE_PATH="${BUDGET_STATE_PATH:-data/budget_state.json}"

if [ ! -f "$SOURCE_PATH" ]; then
  echo "Missing budget state: $SOURCE_PATH" >&2
  echo "Run: python -m src.main one-number-state" >&2
  exit 1
fi

if ! xcrun simctl get_app_container "$SIMULATOR_ID" "$BUNDLE_ID" data >/dev/null 2>&1; then
  echo "App is not installed on simulator $SIMULATOR_ID: $BUNDLE_ID" >&2
  echo "Build and run the app in Simulator first." >&2
  exit 1
fi

GROUP_CONTAINER="$(xcrun simctl get_app_container "$SIMULATOR_ID" "$BUNDLE_ID" "$APP_GROUP_ID")"
mkdir -p "$GROUP_CONTAINER"
cp "$SOURCE_PATH" "$GROUP_CONTAINER/budget_state.json"
echo "Synced $SOURCE_PATH to $GROUP_CONTAINER/budget_state.json"
