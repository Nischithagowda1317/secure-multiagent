from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas import SecurityDecision


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(all\s+)?(secrets?|restricted|confidential)",
    r"show\s+(me\s+)?the\s+system\s+prompt",
    r"bypass\s+(rbac|security|authorization|policy)",
    r"disable\s+(security|audit|logging)",
    r"act\s+as\s+(an?\s+)?admin",
    r"forget\s+(all\s+)?rules",
    r"do\s+not\s+check\s+permissions",
]


@dataclass
class AuthorizationResult:
    decision: SecurityDecision
    injection_detected: bool = False


class RBACService:
    def __init__(self, runtime_store: Any):
        self.runtime_store = runtime_store

    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        lowered = text.lower()
        return any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS)

    def authorize(
        self,
        *,
        user: dict[str, Any],
        permission: str,
        resource_type: str,
        resource_id: str | None = None,
        allowed_roles: list[str] | None = None,
        input_text: str = "",
    ) -> AuthorizationResult:
        roles = list(user.get("roles", []))
        permissions = set(user.get("permissions", []))
        checks = ["authenticated", "active_account", "role_verified", "resource_scope_checked"]
        injection_detected = self.detect_prompt_injection(input_text)
        if injection_detected:
            checks.append("prompt_injection_detected")

        role_ok = not allowed_roles or bool(set(roles).intersection(allowed_roles))
        permission_ok = permission in permissions
        if permission_ok and role_ok:
            decision = "ALLOW"
            reason = "Permission granted by one or more assigned roles."
        else:
            decision = "DENY"
            reasons: list[str] = []
            if not permission_ok:
                reasons.append(f"Required permission '{permission}' is not granted")
            if not role_ok:
                reasons.append("The user's role is outside the allowed resource scope")
            reason = "; ".join(reasons) + "."

        session_risk = 0.08
        if not user.get("mfa_enabled", False):
            session_risk += 0.15
        if injection_detected:
            session_risk += 0.45
        if resource_type in {"salary", "security_document", "purchase", "task_action"}:
            session_risk += 0.12
        session_risk = min(round(session_risk, 3), 1.0)

        model = SecurityDecision(
            decision=decision,
            permission=permission,
            reason=reason,
            roles=roles,
            zero_trust_checks=checks,
            session_risk_score=session_risk,
        )
        self.runtime_store.add_audit(
            user_id=str(user["user_id"]),
            event_type="authorization_decision",
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            details={
                "permission": permission,
                "roles": roles,
                "allowed_roles": allowed_roles or [],
                "zero_trust_checks": checks,
                "session_risk_score": session_risk,
                "prompt_injection_detected": injection_detected,
            },
        )
        return AuthorizationResult(model, injection_detected)
