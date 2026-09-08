from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


WORKLOAD_FEATURES = [
    "total_workload_percent",
    "billable_workload_percent",
    "active_project_count",
    "open_task_count",
    "overdue_task_count",
]

TASK_RISK_NUMERIC = [
    "estimated_hours",
    "actual_hours",
    "progress_percent",
    "days_to_due",
    "hour_overrun_ratio",
    "is_overdue",
]
TASK_RISK_CATEGORICAL = [
    "task_phase",
    "priority",
    "status",
    "requires_approval_for_reassignment",
    "data_classification",
]

SALES_APPROVAL_NUMERIC = [
    "order_quantity",
    "unit_cost_usd",
    "unit_price_usd",
    "discount_percent",
    "cost_of_sales_usd",
    "sales_usd",
    "profit_usd",
]
SALES_APPROVAL_CATEGORICAL = [
    "sales_channel",
    "promotion_name",
    "product_category",
    "region",
    "country",
]

HITL_NUMERIC = [
    "task_complexity",
    "autonomy_level",
    "success_rate",
    "accuracy_score",
    "efficiency_score",
    "execution_time_seconds",
    "response_latency_ms",
    "memory_usage_mb",
    "cpu_usage_percent",
    "cost_per_task_cents",
    "error_recovery_rate",
    "privacy_compliance_score",
    "bias_detection_score",
    "data_quality_score",
    "autonomous_capability_score",
]
HITL_CATEGORICAL = [
    "agent_type",
    "model_architecture",
    "deployment_environment",
    "task_category",
    "multimodal_capability",
    "edge_compatibility",
]


def prepare_task_risk_frame(tasks: pd.DataFrame, snapshot_date: str) -> pd.DataFrame:
    frame = tasks.copy()
    snapshot = pd.Timestamp(snapshot_date)
    due = pd.to_datetime(frame["due_date"], errors="coerce")
    frame["days_to_due"] = (due - snapshot).dt.days.fillna(999).astype(float)
    frame["is_overdue"] = (
        (due < snapshot) & (frame["status"].astype(str) != "Completed")
    ).astype(int)
    estimated = pd.to_numeric(frame["estimated_hours"], errors="coerce").replace(0, np.nan)
    actual = pd.to_numeric(frame["actual_hours"], errors="coerce").fillna(0)
    frame["hour_overrun_ratio"] = (actual / estimated).replace([np.inf, -np.inf], np.nan).fillna(0)
    return frame


def derive_task_risk_label(frame: pd.DataFrame) -> pd.Series:
    blocked = frame["status"].astype(str).str.lower().eq("blocked")
    overdue = frame["is_overdue"].astype(int).eq(1)
    low_progress = pd.to_numeric(frame["progress_percent"], errors="coerce").fillna(0) < 70
    severe_overrun = frame["hour_overrun_ratio"] > 1.35
    critical = frame["priority"].astype(str).str.lower().eq("critical")
    approval = frame["requires_approval_for_reassignment"].astype(str).str.lower().eq("true")

    labels = np.where(
        blocked | (overdue & low_progress) | severe_overrun,
        "High",
        np.where(overdue | critical | approval | (frame["hour_overrun_ratio"] > 1.1), "Medium", "Low"),
    )
    return pd.Series(labels, index=frame.index, name="task_risk_label")


def model_artifact_timestamp(path: Path) -> str | None:
    if not path.exists():
        return None
    return pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC").isoformat()
