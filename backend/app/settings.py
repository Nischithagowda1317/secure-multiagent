from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
# Locally this file is backend/app/settings.py; a Vercel service is flattened
# to /var/task/app/settings.py, with its bundled assets in /var/task.
PROJECT_ROOT = BACKEND_ROOT.parent if BACKEND_ROOT.name == "backend" else BACKEND_ROOT
IS_VERCEL = os.getenv("VERCEL") == "1"
if not IS_VERCEL:
    load_dotenv(PROJECT_ROOT / ".env")


def _env_or_default(name: str, default: str) -> str:
    """Treat empty optional values from deployment settings as unset."""
    return os.getenv(name, "").strip() or default


RUNTIME_ROOT = Path(_env_or_default(
    "RUNTIME_ROOT",
    str(Path(tempfile.gettempdir()) / "enterprise-assistant" if IS_VERCEL else PROJECT_ROOT / "runtime"),
))


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
    runtime_root: Path = RUNTIME_ROOT
    frontend_dist: Path = Path(
        os.getenv("FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist"))
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "academic-demo-change-me-use-a-long-random-secret-2026")
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = int(_env_or_default("JWT_EXP_MINUTES", "480"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    llm_fallback_provider: str = os.getenv(
        "LLM_FALLBACK_PROVIDER", "extractive"
    ).lower()
    openai_api_key: str = field(default=os.getenv("OPENAI_API_KEY", ""), repr=False)
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_timeout_seconds: float = float(
        _env_or_default("OPENAI_TIMEOUT_SECONDS", "120")
    )
    data_backend: str = os.getenv("DATA_BACKEND", "csv").lower()
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://enterprise_user:enterprise_password@127.0.0.1:5432/enterprise_assistant",
    )
    database_schema: str = os.getenv("DATABASE_SCHEMA", "enterprise_ai")
    runtime_backend: str = os.getenv("RUNTIME_BACKEND", "auto").lower()
    rag_backend: str = os.getenv("RAG_BACKEND", "tfidf").lower()
    chroma_path: Path = Path(
        _env_or_default("CHROMA_PATH", str(RUNTIME_ROOT / "chroma"))
    )
    chroma_collection: str = os.getenv(
        "CHROMA_COLLECTION", "enterprise_knowledge"
    )
    max_upload_mb: int = int(_env_or_default("MAX_UPLOAD_MB", "10"))
    router_confidence_threshold: float = float(
        _env_or_default("ROUTER_CONFIDENCE_THRESHOLD", "0.60")
    )
    snapshot_date: str = _env_or_default("DATASET_SNAPSHOT_DATE", "2026-08-28")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    )

    @property
    def uses_postgres(self) -> bool:
        return self.data_backend in {"postgres", "supabase"}

    @property
    def resolved_runtime_backend(self) -> str:
        if self.runtime_backend == "auto":
            return "postgres" if self.uses_postgres else "sqlite"
        if self.runtime_backend not in {"postgres", "sqlite"}:
            raise ValueError("RUNTIME_BACKEND must be auto, postgres, or sqlite.")
        return self.runtime_backend

    def ensure_directories(self) -> None:
        # Models are read-only deployment assets. Training scripts create their
        # own output directories; importing the API must not write there.
        for path in (
            self.runtime_root,
            self.runtime_root / "uploads",
            self.runtime_root / "logs",
            self.runtime_root / "checkpoints",
        ):
            path.mkdir(parents=True, exist_ok=True)
        if self.rag_backend == "chroma":
            self.chroma_path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
