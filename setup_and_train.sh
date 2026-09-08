#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"; print(sys.version)'
[ -d .venv ] || "$PYTHON_BIN" -m venv .venv
PYTHON=".venv/bin/python"
"$PYTHON" -m pip install --upgrade pip setuptools wheel
"$PYTHON" -m pip install -r backend/requirements.txt
[ -f .env ] || cp .env.example .env
"$PYTHON" backend/scripts/init_database.py
"$PYTHON" backend/scripts/train_all.py
"$PYTHON" backend/scripts/validate_install.py
PYTHONPATH=backend "$PYTHON" -m pytest -q backend/tests
"$PYTHON" backend/scripts/smoke_test.py
printf '\nComplete. Run ./run_dashboard.sh and open http://127.0.0.1:8000\n'
