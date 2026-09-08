from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    project_name: str = "Secure Multi-Agent Enterprise Assistant"
    project_root: Path = PROJECT_ROOT
    dataset_root: Path = Path(
        os.getenv(
            "DATASET_ROOT",
            str(PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"),
        )
    )
    models_root: Path = Path(os.getenv("MODELS_ROOT", str(PROJECT_ROOT / "models")))
    runtime_root: Path = Path(os.getenv("RUNTIME_ROOT", str(PROJECT_ROOT / "runtime")))
    frontend_dist: Path = Path(
        os.getenv("FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist"))
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "academic-demo-change-me-use-a-long-random-secret-2026")
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = int(os.getenv("JWT_EXP_MINUTES", "480"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "extractive").lower()
    llm_fallback_provider: str = os.getenv(
        "LLM_FALLBACK_PROVIDER", "extractive"
    ).lower()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_timeout_seconds: float = float(
        os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")
    )
    data_backend: str = os.getenv("DATA_BACKEND", "csv").lower()
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://enterprise_user:enterprise_password@127.0.0.1:5432/enterprise_assistant",
    )
    database_schema: str = os.getenv("DATABASE_SCHEMA", "enterprise_ai")
    rag_backend: str = os.getenv("RAG_BACKEND", "tfidf").lower()
    chroma_path: Path = Path(
        os.getenv("CHROMA_PATH", str(PROJECT_ROOT / "runtime" / "chroma"))
    )
    chroma_collection: str = os.getenv(
        "CHROMA_COLLECTION", "enterprise_knowledge"
    )
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    router_confidence_threshold: float = float(
        os.getenv("ROUTER_CONFIDENCE_THRESHOLD", "0.60")
    )
    snapshot_date: str = os.getenv("DATASET_SNAPSHOT_DATE", "2026-08-28")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    )

    def ensure_directories(self) -> None:
        for path in (
            self.models_root,
            self.runtime_root,
            self.runtime_root / "uploads",
            self.runtime_root / "logs",
            self.runtime_root / "checkpoints",
            self.chroma_path,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
