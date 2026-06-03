#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.ief.lunchmoney.hourly-monitor.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$HOME/Library/Logs/lunchmoney-finance-watcher"
RUNTIME_DIR="$HOME/Library/Application Support/lunchmoney-finance-watcher"

if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

cd "$SCRIPT_DIR"

mkdir -p \
  "$HOME/Library/LaunchAgents" \
  "$LOG_DIR" \
  "$RUNTIME_DIR" \
  "$RUNTIME_DIR/src" \
  "$RUNTIME_DIR/config" \
  "$RUNTIME_DIR/data" \
  "$RUNTIME_DIR/reports"
touch "$LOG_DIR/hourly-monitor.out.log" "$LOG_DIR/hourly-monitor.err.log"

cp "$SCRIPT_DIR/run_hourly_monitor.sh" "$RUNTIME_DIR/run_hourly_monitor.sh"
cp "$SCRIPT_DIR/requirements.txt" "$RUNTIME_DIR/requirements.txt"
cp "$PLIST_SRC" "$PLIST_DST"
chmod +x "$RUNTIME_DIR/run_hourly_monitor.sh"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  cp "$SCRIPT_DIR/.env" "$RUNTIME_DIR/.env"
fi

cp "$SCRIPT_DIR/src/"*.py "$RUNTIME_DIR/src/"
cp "$SCRIPT_DIR/config/"*.yaml "$RUNTIME_DIR/config/"

if [[ ! -x "$RUNTIME_DIR/.venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$RUNTIME_DIR/.venv"
fi

"$RUNTIME_DIR/.venv/bin/python" -m pip --disable-pip-version-check install -r "$RUNTIME_DIR/requirements.txt" >/dev/null

launchctl unload "$PLIST_DST" >/dev/null 2>&1 || true
launchctl load "$PLIST_DST"

echo "Installed: $PLIST_DST"
echo "Label: com.ief.lunchmoney.hourly-monitor"
echo "Runtime: $RUNTIME_DIR"
echo "Logs: $LOG_DIR"
echo "Reports: $RUNTIME_DIR/reports"
echo "Data: $RUNTIME_DIR/data"
echo "Schedule: every hour, plus run at load."
echo "Next step: disable the Codex automation for this watcher to stop Playground inbox items."
