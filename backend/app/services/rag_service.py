from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.repository import DataRepository
from app.services.runtime_store import RuntimeStore
from app.settings import Settings
from app.utils.files import chunk_text
from app.utils.text import pipe_values


class RAGService:
    def __init__(
        self,
        settings: Settings,
        repository: DataRepository,
        runtime_store: RuntimeStore,
    ):
        self.settings = settings
        self.repository = repository
        self.runtime_store = runtime_store
        self.index_path = settings.models_root / "rag" / "rag_index.joblib"
        self.runtime_index_path = settings.runtime_root / "runtime_rag_index.joblib"
        self._base: dict[str, Any] | None = None
        self._runtime: dict[str, Any] | None = None
        self._chroma_collection: Any | None = None
        self._chroma_error: str | None = None

    def load(self) -> None:
        if self.settings.rag_backend == "chroma":
            self._load_chroma()
        elif self.settings.rag_backend != "tfidf":
            raise ValueError(
                f"Unsupported RAG_BACKEND={self.settings.rag_backend!r}. "
                "Use 'tfidf' or 'chroma'."
            )
        if self._base is None and self.index_path.exists():
            self._base = joblib.load(self.index_path)
        if self._runtime is None and self.runtime_index_path.exists():
            self._runtime = joblib.load(self.runtime_index_path)

    def _load_chroma(self) -> None:
        if self._chroma_collection is not None or self._chroma_error is not None:
            return
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
            self._chroma_collection = client.get_collection(
                name=self.settings.chroma_collection
            )
        except Exception as exc:
            # Keep the offline TF-IDF index usable as a fallback. The health
            # endpoint still reports the configured backend so setup problems
            # remain visible to the operator.
            self._chroma_error = str(exc)

    @staticmethod
    def hashing_embeddings(texts: list[str]) -> list[list[float]]:
        vectorizer = HashingVectorizer(
            n_features=4096,
            alternate_sign=False,
            norm="l2",
            stop_words="english",
            ngram_range=(1, 2),
        )
        return vectorizer.transform(texts).astype(np.float32).toarray().tolist()

    def retrieve(
        self,
        query: str,
        roles: list[str],
        permissions: list[str],
        top_k: int = 4,
        temporary_chunks: list[dict[str, Any]] | None = None,
        retrieval_scope: str = "enterprise_only",
        summarize_attachments: bool = False,
    ) -> list[dict[str, Any]]:
        if retrieval_scope not in {
            "attachment_only",
            "enterprise_only",
            "attachment_plus_enterprise",
        }:
            raise ValueError(f"Unsupported retrieval_scope={retrieval_scope!r}")
        temporary_chunks = temporary_chunks or []
        if retrieval_scope == "attachment_only":
            authorized = self._authorized_temporary_chunks(
                temporary_chunks, roles, permissions
            )
            if summarize_attachments:
                return [
                    {**item, "score": 1.0}
                    for item in authorized[: max(top_k, min(len(authorized), 24))]
                ]
            return self._search_temporary(query, authorized, top_k)

        self.load()
        candidates: list[dict[str, Any]] = []
        if self.settings.rag_backend == "chroma" and self._chroma_collection is not None:
            candidates.extend(
                self._search_chroma(query, roles, permissions, top_k * 3)
            )
        elif self._base:
            candidates.extend(
                self._search_index(self._base, query, roles, permissions, top_k * 3)
            )
        if self._runtime:
            candidates.extend(
                self._search_index(self._runtime, query, roles, permissions, top_k * 3)
            )
        if retrieval_scope == "attachment_plus_enterprise" and temporary_chunks:
            temporary_results = self._search_temporary(
                query,
                self._authorized_temporary_chunks(
                    temporary_chunks, roles, permissions
                ),
                top_k * 2,
            )
            # The user explicitly attached these files to the current request.
            # Apply a bounded session-only relevance boost so an attachment with
            # matching terms is not drowned out by the permanent knowledge base.
            for item in temporary_results:
                if float(item.get("score", 0.0)) > 0:
                    item["score"] = round(min(1.0, float(item["score"]) + 0.25), 4)
            candidates.extend(temporary_results)
        candidates.sort(key=lambda item: item["score"], reverse=True)
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in candidates:
            key = f"{item.get('document_id')}::{item.get('chunk_id')}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
            if len(unique) >= top_k:
                break
        return unique

    @staticmethod
    def _authorized_temporary_chunks(
        chunks: list[dict[str, Any]],
        roles: list[str],
        permissions: list[str],
    ) -> list[dict[str, Any]]:
        role_set = set(roles)
        permission_set = set(permissions)
        output = []
        for item in chunks:
            allowed_roles = set(pipe_values(item.get("allowed_roles")))
            required_permission = str(item.get("required_permission") or "")
            if allowed_roles and not role_set.intersection(allowed_roles):
                continue
            if required_permission and required_permission not in permission_set:
                continue
            output.append(dict(item))
        return output

    def _search_chroma(
        self,
        query: str,
        roles: list[str],
        permissions: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        if self._chroma_collection is None:
            return []
        payload = self._chroma_collection.query(
            query_embeddings=self.hashing_embeddings([query]),
            n_results=max(top_k * 3, 10),
            include=["documents", "metadatas", "distances"],
        )
        documents = (payload.get("documents") or [[]])[0]
        metadatas = (payload.get("metadatas") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]
        role_set = set(roles)
        permission_set = set(permissions)
        results: list[dict[str, Any]] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            row = dict(metadata or {})
            allowed_roles = set(pipe_values(row.get("allowed_roles")))
            required_permission = str(row.get("required_permission") or "")
            if allowed_roles and not role_set.intersection(allowed_roles):
                continue
            if required_permission and required_permission not in permission_set:
                continue
            row["chunk_text"] = str(document or "")
            row["score"] = round(max(0.0, 1.0 - float(distance)), 4)
            results.append(row)
            if len(results) >= top_k:
                break
        return results

    def _search_index(
        self,
        index: dict[str, Any],
        query: str,
        roles: list[str],
        permissions: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        vectorizer = index["vectorizer"]
        matrix = index["matrix"]
        metadata = index["metadata"]
        query_vector = vectorizer.transform([query])
        scores = cosine_similarity(query_vector, matrix)[0]
        order = np.argsort(scores)[::-1]
        role_set = set(roles)
        permission_set = set(permissions)
        results: list[dict[str, Any]] = []
        for position in order:
            if scores[position] <= 0:
                continue
            row = dict(metadata[position])
            allowed_roles = set(pipe_values(row.get("allowed_roles")))
            required_permission = str(row.get("required_permission") or "")
            if allowed_roles and not role_set.intersection(allowed_roles):
                continue
            if required_permission and required_permission not in permission_set:
                continue
            row["score"] = round(float(scores[position]), 4)
            results.append(row)
            if len(results) >= top_k:
                break
        return results

    @staticmethod
    def _search_temporary(
        query: str, chunks: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        texts = [str(item["chunk_text"]) for item in chunks]
        if not texts:
            return []
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        matrix = vectorizer.fit_transform(texts + [query])
        scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
        order = np.argsort(scores)[::-1]
        results: list[dict[str, Any]] = []
        for position in order[:top_k]:
            row = dict(chunks[position])
            row["score"] = round(float(scores[position]), 4)
            results.append(row)
        return results

    def build_temporary_chunks(self, title: str, text: str) -> list[dict[str, Any]]:
        document_id = "TEMP-" + hashlib.sha256(
            f"{title}\0{text}".encode("utf-8", errors="replace")
        ).hexdigest()[:12].upper()
        return [
            {
                "chunk_id": f"{document_id}-CH{index + 1:03d}",
                "document_id": document_id,
                "document_title": title,
                "section_number": str(index + 1),
                "section_title": "Uploaded attachment",
                "chunk_text": value,
                "classification": "Session Private",
                "allowed_roles": "",
                "required_permission": "ai.query",
                "source_path": title,
                "source_type": "Temporary upload",
            }
            for index, value in enumerate(chunk_text(text, chunk_size=500, overlap=80))
        ]

    def rebuild_runtime_index(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        for document in self.runtime_store.list_uploaded_documents():
            text_path = Path(document["extracted_text_path"])
            if not text_path.exists():
                continue
            text = text_path.read_text(encoding="utf-8", errors="replace")
            for index, value in enumerate(chunk_text(text, chunk_size=500, overlap=80), start=1):
                records.append(
                    {
                        "chunk_id": f"{document['document_id']}-CH{index:03d}",
                        "document_id": document["document_id"],
                        "document_title": document["title"],
                        "section_number": str(index),
                        "section_title": "Uploaded document",
                        "chunk_text": value,
                        "classification": document["classification"],
                        "allowed_roles": "|".join(document["allowed_roles"]),
                        "required_permission": document["required_permission"],
                        "source_path": document["stored_path"],
                        "source_type": "Uploaded enterprise document",
                    }
                )
        if not records:
            self.runtime_index_path.unlink(missing_ok=True)
            self._runtime = None
            return {"documents": 0, "chunks": 0}
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        matrix = vectorizer.fit_transform([record["chunk_text"] for record in records])
        payload = {"vectorizer": vectorizer, "matrix": matrix, "metadata": records}
        joblib.dump(payload, self.runtime_index_path)
        self._runtime = payload
        return {"documents": len(self.runtime_store.list_uploaded_documents()), "chunks": len(records)}
