#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run ./setup_and_train.sh first"; exit 1; }
.venv/bin/python backend/scripts/check_gpu.py
.venv/bin/python backend/scripts/train_agent_performance_torch.py "$@"
.venv/bin/python backend/scripts/generate_model_manifest.py
