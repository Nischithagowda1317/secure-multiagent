from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from _bootstrap import PROJECT_ROOT
from app.ml.features import SALES_APPROVAL_CATEGORICAL, SALES_APPROVAL_NUMERIC
from training_common import artifact_ready, save_metrics


def train(force: bool = False) -> None:
    output = PROJECT_ROOT / "models" / "sales_approval" / "sales_approval_model.joblib"
    if artifact_ready(output, force):
        print(f"[SKIP] Sales-approval model already exists: {output}")
        return
    data = pd.read_csv(
        PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset" / "core" / "sales_finance" / "sales_orders.csv"
    )
    features = data[SALES_APPROVAL_NUMERIC + SALES_APPROVAL_CATEGORICAL]
    target = data["requires_discount_approval"].astype(bool)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.20, random_state=42, stratify=target
    )
    pipeline = Pipeline(
        [
            (
                "preprocess",
                ColumnTransformer(
                    [
                        ("numeric", StandardScaler(), SALES_APPROVAL_NUMERIC),
                        ("categorical", OneHotEncoder(handle_unknown="ignore"), SALES_APPROVAL_CATEGORICAL),
                    ]
                ),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output)
    save_metrics(
        output.parent / "metrics.json",
        {
            "model": "Preprocessed Logistic Regression discount-approval classifier",
            "dataset_rows": int(len(data)),
            "accuracy": float(accuracy_score(y_test, predictions)),
            "macro_f1": float(f1_score(y_test, predictions, average="macro")),
            "roc_auc": float(roc_auc_score(y_test, probabilities)),
            "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
        },
    )
    print(f"[OK] Sales-approval model saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    train(args.force)
