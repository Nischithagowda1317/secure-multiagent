from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.ml.features import (
    SALES_APPROVAL_CATEGORICAL,
    SALES_APPROVAL_NUMERIC,
    TASK_RISK_CATEGORICAL,
    TASK_RISK_NUMERIC,
    WORKLOAD_FEATURES,
    model_artifact_timestamp,
    prepare_task_risk_frame,
)
from app.settings import Settings
from app.utils.intent import (
    is_reassignment_action,
    is_reassignment_topic,
    reassignment_read_workflow,
)
from app.utils.json_tools import json_safe


class ModelRegistry:
    MODEL_SPECS = {
        "router": ("router/router_model.joblib", "router/metrics.json"),
        "workload": ("workload/workload_model.joblib", "workload/metrics.json"),
        "task_risk": ("task_risk/task_risk_model.joblib", "task_risk/metrics.json"),
        "sales_approval": (
            "sales_approval/sales_approval_model.joblib",
            "sales_approval/metrics.json",
        ),
        "hitl": ("hitl/hitl_model.joblib", "hitl/metrics.json"),
        "agent_performance": (
            "agent_performance/agent_performance_model.joblib",
            "agent_performance/metrics.json",
        ),
        "rag": ("rag/rag_index.joblib", "rag/metrics.json"),
        "agent_performance_nn": (
            "agent_performance_nn/best_model.pt",
            "agent_performance_nn/metrics.json",
        ),
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.models_root
        self._models: dict[str, Any] = {}
        self._load_errors: dict[str, str] = {}

    def path(self, name: str) -> Path:
        return self.root / self.MODEL_SPECS[name][0]

    def load(self, name: str) -> Any | None:
        if name in self._models:
            return self._models[name]
        path = self.path(name)
        if not path.exists() or path.suffix == ".pt":
            return None
        try:
            model = joblib.load(path)
        except Exception as exc:
            self._load_errors[name] = str(exc)
            return None
        self._models[name] = model
        self._load_errors.pop(name, None)
        return model

    def reload(self) -> None:
        self._models.clear()
        self._load_errors.clear()

    def status(self) -> list[dict[str, Any]]:
        values = []
        for name, (artifact_rel, metrics_rel) in self.MODEL_SPECS.items():
            artifact = self.root / artifact_rel
            metrics_path = self.root / metrics_rel
            metrics: dict[str, Any] = {}
            if metrics_path.exists():
                try:
                    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    metrics = {"warning": "Metrics file could not be parsed"}
            values.append(
                {
                    "model_name": name,
                    "artifact_path": str(artifact.relative_to(self.settings.project_root)),
                    "available": artifact.exists(),
                    "metrics": metrics,
                    "trained_at": model_artifact_timestamp(artifact),
                    "load_error": self._load_errors.get(name),
                }
            )
        return values

    def route(self, text: str) -> tuple[str, float]:
        model = self.load("router")
        if model is None:
            return self._heuristic_route(text), 0.70
        prediction = str(model.predict([text])[0])
        probability = 0.85
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba([text])[0]
            probability = float(max(probabilities))
        return prediction, round(probability, 4)

    @staticmethod
    def _heuristic_route(text: str) -> str:
        query = text.lower()
        if "salary" in query or "compensation" in query:
            return "WFD004"
        if is_reassignment_action(text):
            return "WFD005"
        if is_reassignment_topic(text):
            return reassignment_read_workflow(text)
        if "discount" in query and any(word in query for word in ("approve", "exception", "%")):
            return "WFD007"
        if "purchase" in query and any(word in query for word in ("approve", "approval", "request")):
            return "WFD008"
        if any(word in query for word in ("leave", "attendance", "absence")):
            return "WFD009"
        if any(word in query for word in ("agent reliability", "hallucination", "grounding", "pass rate")):
            return "WFD011"
        domains = sum(
            int(any(word in query for word in words))
            for words in (
                ("employee", "workload", "overtime", "hr"),
                ("project", "task", "risk"),
                ("sales", "profit", "revenue", "order"),
                ("finance", "expense", "purchase"),
                ("policy", "document"),
            )
        )
        if domains >= 3:
            return "WFD012"
        if "project" in query and any(word in query for word in ("workload", "overloaded", "employee", "team")):
            return "WFD003"
        if any(word in query for word in ("project", "task", "deadline", "blocked")):
            return "WFD002"
        if any(word in query for word in ("sales", "profit", "revenue", "product", "region", "channel")):
            return "WFD006"
        if any(word in query for word in ("restricted", "confidential", "security policy")):
            return "WFD010"
        return "WFD001"

    def predict_workload(self, frame: pd.DataFrame) -> list[str]:
        model = self.load("workload")
        if model is None:
            return frame["total_workload_percent"].apply(self._workload_rule).tolist()
        return [str(value) for value in model.predict(frame[WORKLOAD_FEATURES])]

    @staticmethod
    def _workload_rule(value: float) -> str:
        if value >= 110:
            return "Overloaded"
        if value >= 90:
            return "High"
        if value >= 60:
            return "Normal"
        return "Available"

    def predict_task_risk(self, tasks: pd.DataFrame) -> list[str]:
        prepared = prepare_task_risk_frame(tasks, self.settings.snapshot_date)
        model = self.load("task_risk")
        if model is None:
            labels = []
            for _, row in prepared.iterrows():
                if row["status"] == "Blocked" or (row["is_overdue"] and row["progress_percent"] < 70):
                    labels.append("High")
                elif row["is_overdue"] or row["priority"] == "Critical":
                    labels.append("Medium")
                else:
                    labels.append("Low")
            return labels
        features = prepared[TASK_RISK_NUMERIC + TASK_RISK_CATEGORICAL]
        return [str(value) for value in model.predict(features)]

    def predict_sales_approval(self, order: pd.DataFrame) -> tuple[bool, float]:
        model = self.load("sales_approval")
        if model is None:
            discount = float(order.iloc[0].get("discount_percent", 0))
            return discount > 10, 0.80
        features = order[SALES_APPROVAL_NUMERIC + SALES_APPROVAL_CATEGORICAL]
        prediction = bool(model.predict(features)[0])
        probability = 0.85
        if hasattr(model, "predict_proba"):
            probability = float(max(model.predict_proba(features)[0]))
        return prediction, round(probability, 4)

    def predict_hitl(self, frame: pd.DataFrame) -> tuple[bool, float]:
        model = self.load("hitl")
        if model is None:
            return bool(frame.iloc[0].get("task_complexity", 1) >= 7), 0.65
        prediction = bool(model.predict(frame)[0])
        probability = 0.80
        if hasattr(model, "predict_proba"):
            probability = float(max(model.predict_proba(frame)[0]))
        return prediction, round(probability, 4)

    def predict_agent_performance(self, frame: pd.DataFrame) -> float | None:
        model = self.load("agent_performance")
        if model is None:
            return None
        return round(float(model.predict(frame)[0]), 5)

    def model_metrics(self, name: str) -> dict[str, Any]:
        metrics_path = self.root / self.MODEL_SPECS[name][1]
        if not metrics_path.exists():
            return {}
        return json_safe(json.loads(metrics_path.read_text(encoding="utf-8")))
