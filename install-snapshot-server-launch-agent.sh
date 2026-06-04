#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.ief.lunchmoney.snapshot-server.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$HOME/Library/Logs/lunchmoney-finance-watcher"
RUNTIME_DIR="$HOME/Library/Application Support/lunchmoney-finance-watcher"
PYTHON_BIN="/usr/bin/python3"

cd "$SCRIPT_DIR"

mkdir -p \
  "$HOME/Library/LaunchAgents" \
  "$LOG_DIR" \
  "$RUNTIME_DIR" \
  "$RUNTIME_DIR/data"
touch "$LOG_DIR/snapshot-server.out.log" "$LOG_DIR/snapshot-server.err.log"

if [[ -f "$SCRIPT_DIR/data/widget_snapshot.json" && ! -f "$RUNTIME_DIR/widget_snapshot.json" ]]; then
  cp "$SCRIPT_DIR/data/widget_snapshot.json" "$RUNTIME_DIR/widget_snapshot.json"
fi

ln -sf ../widget_snapshot.json "$RUNTIME_DIR/data/widget_snapshot.json"
ln -sf ../budget_state.json "$RUNTIME_DIR/data/budget_state.json"

cp "$PLIST_SRC" "$PLIST_DST"
launchctl unload "$PLIST_DST" >/dev/null 2>&1 || true
launchctl load "$PLIST_DST"

echo "Installed: $PLIST_DST"
echo "Label: com.ief.lunchmoney.snapshot-server"
echo "Runtime: $RUNTIME_DIR"
echo "Logs: $LOG_DIR"
echo "URL: http://$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 127.0.0.1):8422/data/widget_snapshot.json"
echo "Python: $PYTHON_BIN"
