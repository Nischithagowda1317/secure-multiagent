#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run ./setup_and_train.sh first"; exit 1; }
export PYTHONPATH="$PWD/backend"
exec .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
