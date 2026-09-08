from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.security.auth import current_user


router = APIRouter(prefix="/api/models", tags=["Model Registry"])


@router.get("")
async def models(request: Request, user=Depends(current_user)):
    services = request.app.state.services
    if "evaluation.read" not in set(user.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Model status requires evaluation.read")
    return services.models.status()


@router.post("/reload")
async def reload_models(request: Request, user=Depends(current_user)):
    services = request.app.state.services
    if "evaluation.manage" not in set(user.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Reloading models requires evaluation.manage")
    services.models.reload()
    services.rag._base = None
    services.rag._runtime = None
    services.rag.load()
    return {"status": "reloaded", "models": services.models.status()}
