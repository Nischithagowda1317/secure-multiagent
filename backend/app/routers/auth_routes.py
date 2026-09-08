from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas import LoginRequest, TokenResponse, UserProfile
from app.security.auth import authenticate, create_access_token, current_user, to_profile


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    services = request.app.state.services
    user = authenticate(services.repository, payload.email, payload.password)
    if not user:
        services.runtime_store.add_audit(
            user_id="UNKNOWN",
            event_type="login_failed",
            resource_type="user",
            resource_id=payload.email,
            decision="DENY",
            details={"email": payload.email},
        )
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(str(user["user_id"]))
    services.runtime_store.add_audit(
        user_id=str(user["user_id"]),
        event_type="login_success",
        resource_type="user",
        resource_id=str(user["user_id"]),
        decision="ALLOW",
        details={"roles": user.get("roles", [])},
    )
    return TokenResponse(access_token=token, user=to_profile(user))


@router.get("/me", response_model=UserProfile)
async def me(user=Depends(current_user)) -> UserProfile:
    return to_profile(user)


@router.get("/demo-accounts")
async def demo_accounts(request: Request):
    accounts = request.app.state.services.repository.demo_accounts()
    return [
        {
            "user_id": account["user_id"],
            "email": account["email"],
            "roles": str(account["roles"]).split("|"),
            "temporary_password": account["temporary_password"],
        }
        for account in accounts
    ]
