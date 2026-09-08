from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas import UserProfile
from app.security.passwords import verify_pbkdf2_sha256
from app.settings import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def authenticate(repository: Any, email: str, password: str) -> dict[str, Any] | None:
    user = repository.user_record(email)
    if not user or user.get("account_status") != "Active":
        return None
    if not verify_pbkdf2_sha256(password, str(user.get("password_hash", ""))):
        return None
    return repository.user_context(str(user["user_id"]))


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_exp_minutes)).timestamp()),
        "aud": "enterprise-assistant",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="enterprise-assistant",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing subject")
        return str(user_id)
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def current_user(
    request: Request, token: str = Depends(oauth2_scheme)
) -> dict[str, Any]:
    user_id = decode_access_token(token)
    repository = request.app.state.services.repository
    user = repository.user_context(user_id)
    if not user or user.get("account_status") != "Active":
        raise HTTPException(status_code=401, detail="User account is not active")
    return user


def to_profile(user: dict[str, Any]) -> UserProfile:
    return UserProfile(
        user_id=str(user["user_id"]),
        employee_id=str(user["employee_id"]),
        email=str(user["email"]),
        username=str(user["username"]),
        full_name=str(user.get("full_name") or user["username"]),
        department_name=user.get("department_name"),
        job_title=user.get("job_title"),
        roles=list(user.get("roles", [])),
        permissions=list(user.get("permissions", [])),
        mfa_enabled=bool(user.get("mfa_enabled", False)),
    )
