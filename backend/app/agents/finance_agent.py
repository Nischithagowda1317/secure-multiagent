from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.agents.types import AgentResult
from app.services.repository import DataRepository
from app.utils.json_tools import json_safe


class FinanceAgent:
    agent_id = "A007"
    agent_name = "Finance Agent"

    def __init__(self, repository: DataRepository):
        self.repository = repository

    def run(self, query: str) -> AgentResult:
        purchases = self.repository.table("purchase_requests").copy()
        expenses = self.repository.table("expense_claims").copy()
        purchase_id = self._id(query, "PUR")
        if purchase_id:
            match = purchases[purchases["purchase_request_id"] == purchase_id]
            if match.empty:
                return AgentResult(
                    self.agent_id,
                    self.agent_name,
                    f"Purchase request {purchase_id} was not found.",
                    {},
                    self._sources(),
                    0.60,
                    ["Check the purchase request identifier."],
                )
            record = json_safe(match.iloc[0].to_dict())
            return AgentResult(
                self.agent_id,
                self.agent_name,
                f"Retrieved purchase request {purchase_id} for approval analysis.",
                {"purchase_request": record, "policy_threshold": self._purchase_threshold(record)},
                self._sources(),
                0.98,
            )

        amount = self._amount(query)
        if amount is not None:
            return AgentResult(
                self.agent_id,
                self.agent_name,
                f"Classified a ${amount:,.2f} purchase against the approval thresholds.",
                {
                    "amount_usd": amount,
                    "required_approval_level": self._threshold_from_amount(amount),
                    "human_approval_required": True,
                },
                self._sources(),
                0.97,
            )

        purchase_status = purchases["status"].value_counts().to_dict()
        expense_status = expenses["status"].value_counts().to_dict()
        content = {
            "purchase_requests": {
                "count": int(len(purchases)),
                "amount_usd": round(float(purchases["amount_usd"].sum()), 2),
                "status_counts": json_safe(purchase_status),
            },
            "expense_claims": {
                "count": int(len(expenses)),
                "amount_usd": round(float(expenses["amount_usd"].sum()), 2),
                "status_counts": json_safe(expense_status),
            },
            "largest_pending_purchases": json_safe(
                purchases[purchases["status"] == "Pending"]
                .sort_values("amount_usd", ascending=False)
                .head(10)
                .to_dict(orient="records")
            ),
        }
        return AgentResult(
            self.agent_id,
            self.agent_name,
            "Prepared the purchase and expense control summary.",
            content,
            self._sources(),
            0.95,
        )

    @staticmethod
    def _purchase_threshold(record: dict[str, Any]) -> str:
        return FinanceAgent._threshold_from_amount(float(record.get("amount_usd", 0)))

    @staticmethod
    def _threshold_from_amount(amount: float) -> str:
        if amount > 100000:
            return "Finance Manager and Executive"
        if amount > 10000:
            return "Finance Manager"
        return "Line Manager / Finance workflow"

    @staticmethod
    def _amount(query: str) -> float | None:
        match = re.search(r"(?:\$|usd\s*)?([0-9][0-9,]*(?:\.\d+)?)", query.lower())
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _id(query: str, prefix: str) -> str | None:
        match = re.search(rf"\b{prefix}\d{{4}}\b", query.upper())
        return match.group(0) if match else None

    @staticmethod
    def _sources() -> list[dict[str, Any]]:
        return [
            {"source_id": "purchase_requests", "title": "purchase_requests.csv", "source_type": "CSV", "path": "core/sales_finance/purchase_requests.csv"},
            {"source_id": "expense_claims", "title": "expense_claims.csv", "source_type": "CSV", "path": "core/sales_finance/expense_claims.csv"},
        ]
