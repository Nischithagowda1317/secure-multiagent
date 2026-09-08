from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.rag_service import RAGService
from app.services.runtime_store import RuntimeStore
from app.settings import Settings
from app.utils.files import chunk_text, extract_text, safe_filename


class DocumentService:
    def __init__(
        self, settings: Settings, runtime_store: RuntimeStore, rag_service: RAGService
    ):
        self.settings = settings
        self.runtime_store = runtime_store
        self.rag_service = rag_service

    def process_temporary(self, filename: str, data: bytes) -> tuple[str, list[dict[str, Any]]]:
        self._validate_size(data)
        text = extract_text(filename, data)
        return text, self.rag_service.build_temporary_chunks(filename, text)

    def persist(
        self,
        *,
        filename: str,
        data: bytes,
        title: str,
        classification: str,
        allowed_roles: list[str],
        required_permission: str,
        uploaded_by: str,
    ) -> dict[str, Any]:
        self._validate_size(data)
        safe_name = safe_filename(filename)
        text = extract_text(safe_name, data)
        upload_dir = self.settings.runtime_root / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / safe_name
        counter = 1
        while file_path.exists():
            file_path = upload_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1
        file_path.write_bytes(data)
        text_path = file_path.with_suffix(file_path.suffix + ".txt")
        text_path.write_text(text, encoding="utf-8")
        record = self.runtime_store.add_uploaded_document(
            title=title or file_path.stem,
            filename=file_path.name,
            classification=classification,
            allowed_roles=allowed_roles,
            required_permission=required_permission,
            stored_path=str(file_path),
            extracted_text_path=str(text_path),
            chunk_count=len(chunk_text(text, chunk_size=500, overlap=80)),
            uploaded_by=uploaded_by,
        )
        self.rag_service.rebuild_runtime_index()
        return record

    def _validate_size(self, data: bytes) -> None:
        limit = self.settings.max_upload_mb * 1024 * 1024
        if len(data) > limit:
            raise ValueError(f"File exceeds the {self.settings.max_upload_mb} MB limit")
