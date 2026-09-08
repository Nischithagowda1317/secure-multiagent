from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    approval_routes,
    audit_routes,
    auth_routes,
    chat_routes,
    dashboard_routes,
    document_routes,
    model_routes,
)
from app.services.container import build_services
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = build_services(settings)
    app.state.services.rag.load()
    yield


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Secure multi-agent enterprise assistant with RAG, RBAC, HITL, XAI, and model monitoring.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(document_routes.router)
app.include_router(approval_routes.router)
app.include_router(model_routes.router)
app.include_router(audit_routes.router)


@app.get("/api/health")
async def health(request: Request):
    llm_status = await request.app.state.services.llm.health_check()
    return {
        "status": "ok",
        "project": settings.project_name,
        "dataset_root": str(settings.dataset_root),
        "models_root": str(settings.models_root),
        "data_backend": settings.data_backend,
        "rag_backend": settings.rag_backend,
        **llm_status,
    }


@app.get("/api/config")
async def public_config():
    return {
        "project_name": settings.project_name,
        "snapshot_date": settings.snapshot_date,
        "max_upload_mb": settings.max_upload_mb,
        "supported_files": ["pdf", "docx", "txt", "csv", "xlsx"],
        "llm_provider": settings.llm_provider,
        "data_backend": settings.data_backend,
        "rag_backend": settings.rag_backend,
    }


if settings.frontend_dist.exists():
    assets = settings.frontend_dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        requested = settings.frontend_dist / full_path
        if full_path and requested.exists() and requested.is_file():
            return FileResponse(requested)
        return FileResponse(settings.frontend_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def no_frontend():
        return {
            "message": "Frontend has not been built yet. Run setup_and_train.ps1 or npm run build in frontend.",
            "api_docs": "/docs",
        }
