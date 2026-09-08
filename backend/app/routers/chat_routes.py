from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.schemas import ChatResponse
from app.security.auth import current_user


router = APIRouter(prefix="/api", tags=["Enterprise Assistant"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    message: Annotated[str, Form()] = "",
    files: list[UploadFile] | None = File(default=None),
    user=Depends(current_user),
) -> ChatResponse:
    services = request.app.state.services
    temporary_chunks = []
    attached_files = []
    for upload in files or []:
        data = await upload.read()
        try:
            extracted_text, chunks = services.documents.process_temporary(
                upload.filename or "attachment", data
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        temporary_chunks.extend(chunks)
        attached_files.append(
            {
                "filename": upload.filename or "attachment",
                "content_type": upload.content_type or "application/octet-stream",
                "size_bytes": len(data),
                "extracted_text": extracted_text,
                "chunk_count": len(chunks),
            }
        )
    if not message.strip() and not attached_files:
        raise HTTPException(status_code=422, detail="Enter a message or attach a file.")
    return await services.orchestrator.run(
        query=message.strip(),
        user=user,
        temporary_chunks=temporary_chunks,
        attached_files=attached_files,
    )
