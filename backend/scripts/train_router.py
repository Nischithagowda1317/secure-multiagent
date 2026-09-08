from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression

from _bootstrap import PROJECT_ROOT
from training_common import artifact_ready, save_metrics


def train(force: bool = False) -> None:
    output = PROJECT_ROOT / "models" / "router" / "router_model.joblib"
    metrics_path = output.parent / "metrics.json"
    if artifact_ready(output, force):
        print(f"[SKIP] Router model already exists: {output}")
        return
    data = pd.read_csv(
        PROJECT_ROOT
        / "datasets"
        / "Secure_Multi_Agent_Enterprise_Dataset"
        / "core"
        / "evaluation"
        / "routing_test_cases.csv"
    )
    x_train, x_test, y_train, y_test = train_test_split(
        data["input_text"].astype(str),
        data["expected_workflow_definition_id"].astype(str),
        test_size=0.25,
        random_state=42,
        stratify=data["expected_workflow_definition_id"],
    )
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    min_df=1,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    lowercase=True,
                    ngram_range=(3, 5),
                    sublinear_tf=True,
                    min_df=1,
                ),
            ),
        ]
    )
    pipeline = Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    max_iter=4000,
                    class_weight="balanced",
                    random_state=42,
                    C=4.0,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output)
    metrics = {
        "model": "TF-IDF word+character Logistic Regression router",
        "dataset_rows": int(len(data)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "classes": sorted(data["expected_workflow_definition_id"].unique().tolist()),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, average="macro")),
        "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
    }
    save_metrics(metrics_path, metrics)
    print(f"[OK] Router model saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    train(args.force)
