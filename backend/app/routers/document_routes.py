from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.security.auth import current_user
from app.utils.json_tools import json_safe
from app.utils.text import pipe_values


router = APIRouter(prefix="/api/documents", tags=["Knowledge Base"])


@router.get("")
async def list_documents(request: Request, user=Depends(current_user)):
    services = request.app.state.services
    roles = set(user.get("roles", []))
    permissions = set(user.get("permissions", []))
    catalog = services.repository.table("document_catalog")
    records = []
    for _, row in catalog.iterrows():
        allowed_roles = set(pipe_values(row.get("allowed_roles")))
        required = str(row.get("required_permission", ""))
        if roles.intersection(allowed_roles) and required in permissions:
            item = json_safe(row.to_dict())
            item["origin"] = "curated"
            records.append(item)
    for item in services.runtime_store.list_uploaded_documents():
        if set(item["allowed_roles"]).intersection(roles) and item["required_permission"] in permissions:
            item["origin"] = "uploaded"
            records.append(item)
    return records


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: Annotated[str, Form()] = "",
    classification: Annotated[str, Form()] = "Internal",
    allowed_roles: Annotated[str, Form()] = "Admin|Executive|HR_Manager|Project_Manager|Finance_Manager|Sales_Manager|Security_Officer|Employee|Auditor|AI_Reviewer",
    required_permission: Annotated[str, Form()] = "document.read_public",
    user=Depends(current_user),
):
    services = request.app.state.services
    authorization = services.rbac.authorize(
        user=user,
        permission="document.upload",
        resource_type="document",
        resource_id=file.filename,
        input_text=f"upload document {file.filename}",
    )
    if authorization.decision.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=authorization.decision.reason)
    data = await file.read()
    try:
        record = services.documents.persist(
            filename=file.filename or "document",
            data=data,
            title=title or (file.filename or "Uploaded document"),
            classification=classification,
            allowed_roles=[part.strip() for part in allowed_roles.split("|") if part.strip()],
            required_permission=required_permission,
            uploaded_by=str(user["user_id"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    services.runtime_store.add_audit(
        user_id=str(user["user_id"]),
        event_type="document_uploaded",
        resource_type="document",
        resource_id=record["document_id"],
        decision="ALLOW",
        details={"filename": record["filename"], "classification": classification},
    )
    return record


@router.post("/rebuild-index")
async def rebuild_index(request: Request, user=Depends(current_user)):
    services = request.app.state.services
    authorization = services.rbac.authorize(
        user=user,
        permission="document.upload",
        resource_type="document_index",
        input_text="rebuild document index",
    )
    if authorization.decision.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=authorization.decision.reason)
    return services.rag.rebuild_runtime_index()
