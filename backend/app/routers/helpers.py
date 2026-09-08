from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def require_permission(user: dict[str, Any], permission: str) -> None:
    if permission not in set(user.get("permissions", [])):
        raise HTTPException(
            status_code=403,
            detail=f"This operation requires the '{permission}' permission.",
        )
