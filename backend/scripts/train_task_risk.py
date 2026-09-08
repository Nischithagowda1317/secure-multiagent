from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from _bootstrap import PROJECT_ROOT
from app.ml.features import (
    TASK_RISK_CATEGORICAL,
    TASK_RISK_NUMERIC,
    derive_task_risk_label,
    prepare_task_risk_frame,
)
from training_common import artifact_ready, save_metrics


def train(force: bool = False) -> None:
    output = PROJECT_ROOT / "models" / "task_risk" / "task_risk_model.joblib"
    if artifact_ready(output, force):
        print(f"[SKIP] Task-risk model already exists: {output}")
        return
    data = pd.read_csv(
        PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset" / "core" / "projects" / "tasks.csv"
    )
    prepared = prepare_task_risk_frame(data, "2026-08-28")
    target = derive_task_risk_label(prepared)
    features = prepared[TASK_RISK_NUMERIC + TASK_RISK_CATEGORICAL]
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=42,
        stratify=target,
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", StandardScaler(), TASK_RISK_NUMERIC),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), TASK_RISK_CATEGORICAL),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocess", preprocessor),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=18,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
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
            "model": "Preprocessed RandomForest task delivery-risk classifier",
            "dataset_rows": int(len(data)),
            "label_note": "Labels are deterministic academic risk labels derived from blocked, overdue, progress, priority, approval, and effort-overrun indicators.",
            "class_distribution": target.value_counts().to_dict(),
            "accuracy": float(accuracy_score(y_test, predictions)),
            "macro_f1": float(f1_score(y_test, predictions, average="macro")),
            "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
        },
    )
    print(f"[OK] Task-risk model saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    train(args.force)
