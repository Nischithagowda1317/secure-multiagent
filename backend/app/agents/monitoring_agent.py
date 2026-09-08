from __future__ import annotations

from typing import Any

import pandas as pd

from app.agents.types import AgentResult
from app.services.repository import DataRepository
from app.utils.json_tools import json_safe


class MonitoringAgent:
    agent_id = "A011"
    agent_name = "Monitoring Agent"

    def __init__(self, repository: DataRepository):
        self.repository = repository

    def run(self, query: str) -> AgentResult:
        metrics = self.repository.table("daily_metrics").copy()
        runs = self.repository.table("workflow_runs").copy()
        judges = self.repository.table("judge_results").copy()
        metrics["metric_date"] = pd.to_datetime(metrics["metric_date"], errors="coerce")
        latest_date = metrics["metric_date"].max()
        latest = metrics[metrics["metric_date"] == latest_date]
        summary_metrics = {
            "snapshot_date": str(latest_date.date()) if pd.notna(latest_date) else None,
            "average_pass_rate": round(float(latest["pass_rate"].mean()), 4),
            "average_review_rate": round(float(latest["review_rate"].mean()), 4),
            "average_regression_rate": round(float(latest["regression_rate"].mean()), 4),
            "average_hallucination_rate": round(float(latest["hallucination_rate"].mean()), 4),
            "judge_human_disagreement_rate": round(float(latest["judge_human_disagreement_rate"].mean()), 4),
            "workflow_status_counts": json_safe(runs["status"].value_counts().to_dict()),
            "average_workflow_execution_ms": round(float(runs["execution_time_ms"].mean()), 2),
            "average_workflow_confidence": round(float(runs["confidence_score"].mean()), 4),
            "average_grounding_score": round(float(runs["grounding_score"].mean()), 4),
            "judge_error_types": json_safe(judges["error_type"].fillna("None").value_counts().head(10).to_dict()),
        }
        return AgentResult(
            self.agent_id,
            self.agent_name,
            "Aggregated agent reliability, hallucination, grounding, workflow, and review metrics.",
            summary_metrics,
            [
                {"source_id": "daily_metrics", "title": "daily_evaluation_metrics.csv", "source_type": "CSV", "path": "core/evaluation/daily_evaluation_metrics.csv"},
                {"source_id": "workflow_runs", "title": "workflow_runs.csv", "source_type": "CSV", "path": "core/agents/workflow_runs.csv"},
                {"source_id": "judge_results", "title": "judge_results.csv", "source_type": "CSV", "path": "core/evaluation/judge_results.csv"},
            ],
            0.98,
        )
