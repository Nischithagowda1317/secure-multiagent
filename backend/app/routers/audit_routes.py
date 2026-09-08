from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.security.auth import current_user
from app.utils.json_tools import json_safe


router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("")
async def audit(request: Request, limit: int = 50, user=Depends(current_user)):
    services = request.app.state.services
    if "audit.read" not in set(user.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Audit access requires audit.read")
    runtime = services.runtime_store.recent_audit(min(max(limit, 1), 200))
    source_frame = services.repository.table("audit_logs").tail(min(max(limit, 1), 100))
    return {
        "runtime": runtime,
        "dataset": json_safe(source_frame.to_dict(orient="records")),
    }
