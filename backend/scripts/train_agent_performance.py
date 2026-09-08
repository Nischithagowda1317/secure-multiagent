from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from _bootstrap import PROJECT_ROOT
from app.ml.features import HITL_CATEGORICAL, HITL_NUMERIC
from training_common import artifact_ready, save_metrics


def train(force: bool = False) -> None:
    output = PROJECT_ROOT / "models" / "agent_performance" / "agent_performance_model.joblib"
    if artifact_ready(output, force):
        print(f"[SKIP] Agent-performance model already exists: {output}")
        return
    data = pd.read_csv(
        PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset" / "raw_sources" / "agentic_ai_performance_source.csv"
    )
    features = data[HITL_NUMERIC + HITL_CATEGORICAL]
    target = data["performance_index"].astype(float)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.20, random_state=42
    )
    pipeline = Pipeline(
        [
            (
                "preprocess",
                ColumnTransformer(
                    [
                        ("numeric", StandardScaler(), HITL_NUMERIC),
                        ("categorical", OneHotEncoder(handle_unknown="ignore"), HITL_CATEGORICAL),
                    ]
                ),
            ),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=400,
                    max_depth=18,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output)
    save_metrics(
        output.parent / "metrics.json",
        {
            "model": "RandomForest agent performance-index regressor",
            "dataset_rows": int(len(data)),
            "mae": float(mean_absolute_error(y_test, predictions)),
            "rmse": float(mean_squared_error(y_test, predictions) ** 0.5),
            "r2": float(r2_score(y_test, predictions)),
        },
    )
    print(f"[OK] Agent-performance model saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    train(args.force)
