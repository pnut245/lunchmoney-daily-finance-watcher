#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [ ! -x .venv/bin/python ]; then
  echo "Missing virtual environment. Create it first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

DEFAULT_INPUT_PATH="$(pwd)/budget_state.json"
DEFAULT_OUTPUT_PATH="$(pwd)/lockscreen_latest.png"

if [ ! -f "$DEFAULT_INPUT_PATH" ]; then
  DEFAULT_INPUT_PATH="$(pwd)/data/budget_state.json"
fi

if [ ! -d "$(dirname "$DEFAULT_OUTPUT_PATH")" ]; then
  DEFAULT_OUTPUT_PATH="$(pwd)/data/lockscreen_latest.png"
fi

INPUT_PATH="${BUDGET_STATE_PATH:-$DEFAULT_INPUT_PATH}"
OUTPUT_PATH="${LOCKSCREEN_OUTPUT_PATH:-$DEFAULT_OUTPUT_PATH}"

.venv/bin/python -m src.lockscreen "$INPUT_PATH" "$OUTPUT_PATH"
