#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

.venv/bin/pip --disable-pip-version-check install -r requirements.txt >/dev/null

output="$(
  .venv/bin/python -m src.main monitor
)"

printf '%s\n' "$output"

active_alarms="$(
  printf '%s\n' "$output" |
    sed -n 's/.*with \([0-9][0-9]*\) active alarm(s).*/\1/p' |
    tail -1
)"

if [ -z "$active_alarms" ]; then
  echo "FINANCE_WATCH_STATUS=ERROR_COULD_NOT_PARSE_ALARM_COUNT"
elif [ "$active_alarms" -gt 0 ]; then
  echo "FINANCE_WATCH_STATUS=NOTIFY"
  echo "FINANCE_ACTIVE_ALARMS=$active_alarms"
else
  echo "FINANCE_WATCH_STATUS=QUIET"
  echo "FINANCE_ACTIVE_ALARMS=0"
fi
