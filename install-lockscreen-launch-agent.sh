#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.ief.lockscreen.refresh.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$HOME/Library/Logs/ief-lockscreen"
RUNTIME_DIR="$HOME/Library/Application Support/ief-lockscreen"

cd "$SCRIPT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing virtual environment. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

".venv/bin/python" -m pip --disable-pip-version-check install -r requirements.txt >/dev/null

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR" "$RUNTIME_DIR" "$RUNTIME_DIR/src"
touch "$LOG_DIR/refresh.out.log" "$LOG_DIR/refresh.err.log"

cp "$SCRIPT_DIR/run_lockscreen_refresh.sh" "$RUNTIME_DIR/run_lockscreen_refresh.sh"
cp "$SCRIPT_DIR/requirements.txt" "$RUNTIME_DIR/requirements.txt"
cp "$SCRIPT_DIR/src/__init__.py" "$RUNTIME_DIR/src/__init__.py"
cp "$SCRIPT_DIR/src/lockscreen.py" "$RUNTIME_DIR/src/lockscreen.py"
cp "$SCRIPT_DIR/src/wallpaper.py" "$RUNTIME_DIR/src/wallpaper.py"
chmod +x "$RUNTIME_DIR/run_lockscreen_refresh.sh"

if [[ ! -f "$RUNTIME_DIR/budget_state.json" ]]; then
  cp "$SCRIPT_DIR/data/budget_state.json" "$RUNTIME_DIR/budget_state.json"
fi

if [[ ! -x "$RUNTIME_DIR/.venv/bin/python" ]]; then
  /usr/bin/python3 -m venv "$RUNTIME_DIR/.venv"
fi

"$RUNTIME_DIR/.venv/bin/python" -m pip --disable-pip-version-check install -r "$RUNTIME_DIR/requirements.txt" >/dev/null

cp "$PLIST_SRC" "$PLIST_DST"
launchctl unload "$PLIST_DST" >/dev/null 2>&1 || true
launchctl load "$PLIST_DST"

echo "Installed: $PLIST_DST"
echo "Logs: $LOG_DIR"
echo "Runtime: $RUNTIME_DIR"
echo "Input JSON: ${BUDGET_STATE_PATH:-$RUNTIME_DIR/budget_state.json}"
echo "Output PNG: ${LOCKSCREEN_OUTPUT_PATH:-$RUNTIME_DIR/lockscreen_latest.png}"
echo "Wallpaper apply: enabled by default (set LOCKSCREEN_APPLY_WALLPAPER=0 to render only)"
echo "Schedule: every 15 minutes, plus run at load."
