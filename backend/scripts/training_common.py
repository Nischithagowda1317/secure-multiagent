from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from _bootstrap import PROJECT_ROOT  # noqa: F401
from app.utils.json_tools import json_safe


def save_metrics(path: Path, metrics: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        **json_safe(metrics),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def artifact_ready(path: Path, force: bool) -> bool:
    """Return True only when an existing artifact is loadable in this environment.

    Scikit-learn/joblib artifacts are not guaranteed to be portable across all
    library versions. Setup therefore retrains an existing file automatically
    when it cannot be loaded, instead of failing later inside the dashboard.
    """
    if force or not path.exists():
        return False
    if path.suffix.lower() == ".joblib":
        try:
            joblib.load(path)
        except Exception as exc:
            print(f"[RETRAIN] Existing artifact is incompatible: {path} ({exc})")
            return False
    return True
