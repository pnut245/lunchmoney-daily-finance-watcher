#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

.venv/bin/pip --disable-pip-version-check install -r requirements.txt >/dev/null
.venv/bin/python -m src.main run-all "$@"
