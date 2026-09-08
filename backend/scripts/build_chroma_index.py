from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from _bootstrap import PROJECT_ROOT
from app.services.rag_service import RAGService


def main(force: bool, collection_name: str, chroma_path: Path) -> None:
    try:
        import chromadb
    except ImportError as exc:
        raise SystemExit(
            "ChromaDB is not installed. Run:\n"
            "  pip install -r backend/requirements-vector.txt"
        ) from exc

    if force and chroma_path.exists():
        shutil.rmtree(chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)

    dataset_root = (
        PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"
    )
    chunks = pd.read_csv(dataset_root / "core" / "rag" / "rag_chunks.csv")
    chunks = chunks[chunks["active"].astype(bool)].copy()

    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )

    ids = chunks["chunk_id"].astype(str).tolist()
    documents = chunks["chunk_text"].fillna("").astype(str).tolist()
    embeddings = RAGService.hashing_embeddings(documents)
    metadatas = []
    keep = [
        "chunk_id",
        "document_id",
        "document_title",
        "section_number",
        "section_title",
        "classification",
        "allowed_roles",
        "required_permission",
        "source_path",
        "version",
        "source_type",
    ]
    for record in chunks.to_dict(orient="records"):
        metadata = {}
        for key in keep:
            value = record.get(key, "")
            if pd.isna(value):
                value = ""
            if isinstance(value, (int, float, bool, str)):
                metadata[key] = value
            else:
                metadata[key] = str(value)
        metadata.setdefault("source_type", "Curated enterprise knowledge")
        metadatas.append(metadata)

    batch_size = 100
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"Indexed {min(end, len(ids))}/{len(ids)} chunks")

    metrics_path = PROJECT_ROOT / "models" / "rag" / "chroma_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(
            {
                "built_at": datetime.now(timezone.utc).isoformat(),
                "backend": "ChromaDB",
                "embedding": "Deterministic scikit-learn HashingVectorizer, 4096 dimensions",
                "collection": collection_name,
                "path": str(chroma_path.relative_to(PROJECT_ROOT)),
                "documents": int(chunks["document_id"].nunique()),
                "chunks": int(len(chunks)),
                "security_filtering": "allowed_roles and required_permission are enforced after vector retrieval",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[OK] Chroma collection '{collection_name}' saved to {chroma_path}")
    print("Set RAG_BACKEND=chroma in .env to use it.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the optional persistent ChromaDB RAG index.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION", "enterprise_knowledge"),
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(os.getenv("CHROMA_PATH", str(PROJECT_ROOT / "runtime" / "chroma"))),
    )
    args = parser.parse_args()
    main(args.force, args.collection, args.path)
