from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.agents.types import AgentResult
from app.ml.registry import ModelRegistry
from app.services.repository import DataRepository
from app.utils.json_tools import json_safe
from app.utils.text import first_match


class SalesAgent:
    agent_id = "A006"
    agent_name = "Sales Analytics Agent"

    def __init__(self, repository: DataRepository, models: ModelRegistry):
        self.repository = repository
        self.models = models

    def run(self, query: str) -> AgentResult:
        orders = self.repository.table("sales_orders").copy()
        filters: dict[str, str] = {}
        for column in ("region", "country", "product_category", "sales_channel", "manufacturer"):
            value = first_match(query, orders[column].dropna().astype(str).unique())
            if value:
                filters[column] = value
                orders = orders[orders[column].astype(str).str.lower() == value.lower()]

        total_sales = float(orders["sales_usd"].sum())
        total_profit = float(orders["profit_usd"].sum())
        margin = (total_profit / total_sales * 100) if total_sales else 0.0
        top_categories = self._aggregate(orders, "product_category")
        top_regions = self._aggregate(orders, "region")
        top_channels = self._aggregate(orders, "sales_channel")
        negative_orders = orders[orders["profit_usd"] < 0]
        content: dict[str, Any] = {
            "filters": filters,
            "kpis": {
                "orders": int(len(orders)),
                "sales_usd": round(total_sales, 2),
                "profit_usd": round(total_profit, 2),
                "profit_margin_percent": round(margin, 2),
                "negative_profit_orders": int(len(negative_orders)),
                "discount_approval_orders": int(orders["requires_discount_approval"].astype(bool).sum()),
            },
            "top_categories": top_categories,
            "top_regions": top_regions,
            "top_channels": top_channels,
            "recommendations": self._recommendations(margin, negative_orders, orders),
        }

        discount = self._discount_from_query(query)
        if discount is not None:
            synthetic = self._representative_order(orders, discount)
            approval, probability = self.models.predict_sales_approval(synthetic)
            content["discount_assessment"] = {
                "requested_discount_percent": discount,
                "model_requires_approval": approval,
                "model_confidence": probability,
                "policy_note": ">10% requires Finance; >20% requires Finance and Executive approval.",
            }

        scope = ", ".join(f"{key}={value}" for key, value in filters.items()) or "all sales"
        summary = (
            f"Analyzed {len(orders)} orders for {scope}: sales ${total_sales:,.2f}, "
            f"profit ${total_profit:,.2f}, margin {margin:.2f}%."
        )
        return AgentResult(
            self.agent_id,
            self.agent_name,
            summary,
            content,
            [
                {
                    "source_id": "sales_orders",
                    "title": "sales_orders.csv",
                    "source_type": "CSV",
                    "path": "core/sales_finance/sales_orders.csv",
                }
            ],
            0.96 if len(orders) else 0.70,
            [] if len(orders) else ["No sales rows matched the detected filters."],
        )

    @staticmethod
    def _aggregate(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        grouped = (
            frame.groupby(column)
            .agg(orders=("order_id", "count"), sales_usd=("sales_usd", "sum"), profit_usd=("profit_usd", "sum"))
            .reset_index()
        )
        grouped["profit_margin_percent"] = (
            grouped["profit_usd"] / grouped["sales_usd"].replace(0, pd.NA) * 100
        ).fillna(0)
        grouped = grouped.sort_values("sales_usd", ascending=False).head(8).round(2)
        return json_safe(grouped.to_dict(orient="records"))

    @staticmethod
    def _recommendations(margin: float, negative_orders: pd.DataFrame, orders: pd.DataFrame) -> list[str]:
        values: list[str] = []
        if margin < 15:
            values.append("Review discounting, product mix, and cost of sales because margin is below 15%.")
        if len(negative_orders):
            values.append("Investigate negative-profit orders and prevent repeat pricing exceptions.")
        if not orders.empty:
            category = orders.groupby("product_category")["profit_usd"].sum().idxmax()
            values.append(f"Protect inventory and campaign coverage for the strongest profit category: {category}.")
        return values or ["Maintain current pricing controls and monitor category-level margin."]

    @staticmethod
    def _discount_from_query(query: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", query)
        return float(match.group(1)) if match else None

    def _representative_order(self, orders: pd.DataFrame, discount: float) -> pd.DataFrame:
        source = orders if not orders.empty else self.repository.table("sales_orders")
        row = source.iloc[[0]].copy()
        row.loc[:, "discount_percent"] = discount
        return row
