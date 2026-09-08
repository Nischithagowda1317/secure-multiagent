from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

from _bootstrap import PROJECT_ROOT
from app.ml.features import WORKLOAD_FEATURES
from training_common import artifact_ready, save_metrics


def train(force: bool = False) -> None:
    output = PROJECT_ROOT / "models" / "workload" / "workload_model.joblib"
    if artifact_ready(output, force):
        print(f"[SKIP] Workload model already exists: {output}")
        return
    data = pd.read_csv(
        PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset" / "core" / "hr" / "employee_workload_snapshots.csv"
    )
    x_train, x_test, y_train, y_test = train_test_split(
        data[WORKLOAD_FEATURES],
        data["workload_status"].astype(str),
        test_size=0.20,
        random_state=42,
        stratify=data["workload_status"],
    )
    model = RandomForestClassifier(
        n_estimators=350,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    save_metrics(
        output.parent / "metrics.json",
        {
            "model": "RandomForest workload-status classifier",
            "dataset_rows": int(len(data)),
            "features": WORKLOAD_FEATURES,
            "accuracy": float(accuracy_score(y_test, predictions)),
            "macro_f1": float(f1_score(y_test, predictions, average="macro")),
            "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
            "feature_importance": dict(zip(WORKLOAD_FEATURES, model.feature_importances_.tolist())),
        },
    )
    print(f"[OK] Workload model saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    train(args.force)
