from __future__ import annotations

from typing import Any

from app.agents.types import AgentResult
from app.schemas import SecurityDecision
from app.security.rbac import AuthorizationResult, RBACService


class SecurityAgent:
    agent_id = "A002"
    agent_name = "Security Agent"

    def __init__(self, rbac: RBACService):
        self.rbac = rbac

    def check(
        self,
        *,
        user: dict[str, Any],
        permission: str,
        resource_type: str,
        resource_id: str | None,
        query: str,
        allowed_roles: list[str] | None = None,
    ) -> tuple[AuthorizationResult, AgentResult]:
        return self.check_many(
            user=user,
            permissions=[permission],
            resource_type=resource_type,
            resource_id=resource_id,
            query=query,
            allowed_roles=allowed_roles,
        )

    def check_many(
        self,
        *,
        user: dict[str, Any],
        permissions: list[str],
        resource_type: str,
        resource_id: str | None,
        query: str,
        allowed_roles: list[str] | None = None,
    ) -> tuple[AuthorizationResult, AgentResult]:
        results = [
            self.rbac.authorize(
                user=user,
                permission=permission,
                resource_type=resource_type,
                resource_id=resource_id,
                allowed_roles=allowed_roles,
                input_text=query,
            )
            for permission in permissions
        ]
        denied = [item for item in results if item.decision.decision != "ALLOW"]
        injection_detected = any(item.injection_detected for item in results)
        if denied:
            decision = SecurityDecision(
                decision="DENY",
                permission=" + ".join(permissions),
                reason="; ".join(item.decision.reason for item in denied),
                roles=list(user.get("roles", [])),
                zero_trust_checks=list(
                    dict.fromkeys(
                        check
                        for item in results
                        for check in item.decision.zero_trust_checks
                    )
                ),
                session_risk_score=max(item.decision.session_risk_score for item in results),
            )
        else:
            decision = SecurityDecision(
                decision="ALLOW",
                permission=" + ".join(permissions),
                reason="All required permissions were granted by the user's assigned roles.",
                roles=list(user.get("roles", [])),
                zero_trust_checks=list(
                    dict.fromkeys(
                        check
                        for item in results
                        for check in item.decision.zero_trust_checks
                    )
                ),
                session_risk_score=max(item.decision.session_risk_score for item in results),
            )
        authorization = AuthorizationResult(decision, injection_detected)
        warnings = []
        if injection_detected:
            warnings.append(
                "Potential prompt-injection language was detected. Embedded instructions were treated as untrusted data."
            )
        result = AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            summary=f"{decision.decision}: {decision.reason}",
            content=decision.model_dump(),
            sources=[
                {
                    "source_id": "rbac",
                    "title": "Role-Permission Policy",
                    "source_type": "Deterministic RBAC",
                    "path": "core/identity_access/role_permissions.csv",
                }
            ],
            confidence=1.0,
            warnings=warnings,
        )
        return authorization, result
