from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if pd.isna(value) if not isinstance(value, (str, bytes)) else False:
        return None
    return value


def dumps(value: Any) -> str:
    return json.dumps(json_safe(value), ensure_ascii=False, separators=(",", ":"))
