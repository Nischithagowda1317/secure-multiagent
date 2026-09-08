from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from _bootstrap import PROJECT_ROOT
from training_common import artifact_ready, save_metrics


def train(force: bool = False) -> None:
    output = PROJECT_ROOT / "models" / "rag" / "rag_index.joblib"
    if artifact_ready(output, force):
        print(f"[SKIP] RAG index already exists: {output}")
        return
    root = PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"
    chunks = pd.read_csv(root / "core" / "rag" / "rag_chunks.csv", encoding="utf-8-sig")
    chunks = chunks[chunks["active"].astype(bool)].copy()
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=25000,
    )
    matrix = vectorizer.fit_transform(chunks["chunk_text"].astype(str))
    metadata = chunks.to_dict(orient="records")
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "metadata": metadata}, output)

    questions = pd.read_csv(root / "core" / "rag" / "rag_evaluation_questions.csv")
    top1 = 0
    top3 = 0
    for _, row in questions.iterrows():
        scores = cosine_similarity(vectorizer.transform([str(row["question"])]), matrix)[0]
        positions = scores.argsort()[::-1][:3]
        documents = [str(metadata[pos]["document_id"]) for pos in positions]
        expected = str(row["expected_document_id"])
        top1 += int(documents and documents[0] == expected)
        top3 += int(expected in documents)
    save_metrics(
        output.parent / "metrics.json",
        {
            "model": "TF-IDF secure RAG retrieval index",
            "documents": int(chunks["document_id"].nunique()),
            "chunks": int(len(chunks)),
            "vocabulary_size": int(len(vectorizer.vocabulary_)),
            "gold_questions": int(len(questions)),
            "unfiltered_top1_document_accuracy": top1 / len(questions),
            "unfiltered_top3_document_accuracy": top3 / len(questions),
            "note": "Runtime retrieval additionally enforces allowed_roles and required_permission before returning evidence.",
        },
    )
    print(f"[OK] RAG index saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    train(args.force)
