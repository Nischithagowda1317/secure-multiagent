from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class UserProfile(BaseModel):
    user_id: str
    employee_id: str
    email: str
    username: str
    full_name: str
    department_name: str | None = None
    job_title: str | None = None
    roles: list[str]
    permissions: list[str]
    mfa_enabled: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class SecurityDecision(BaseModel):
    decision: str
    permission: str
    reason: str
    roles: list[str]
    zero_trust_checks: list[str]
    session_risk_score: float = 0.0


class AgentTrace(BaseModel):
    sequence: int
    agent_id: str
    agent_name: str
    status: str
    duration_ms: int
    summary: str
    confidence: float = 1.0


class SourceReference(BaseModel):
    source_id: str
    title: str
    source_type: str
    section: str | None = None
    path: str | None = None
    score: float | None = None


class ApprovalInfo(BaseModel):
    required: bool = False
    approval_id: str | None = None
    status: str | None = None
    required_roles: list[str] = Field(default_factory=list)
    reason: str | None = None


class ChatResponse(BaseModel):
    workflow_run_id: str
    workflow_id: str
    workflow_name: str
    status: str
    answer: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    security: SecurityDecision
    agents: list[AgentTrace] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: float
    grounding_score: float
    approval: ApprovalInfo = Field(default_factory=ApprovalInfo)
    explanation: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ApprovalDecisionRequest(BaseModel):
    decision: str
    comment: str = ""


class ModelStatus(BaseModel):
    model_name: str
    artifact_path: str
    available: bool
    metrics: dict[str, Any] = Field(default_factory=dict)
    trained_at: str | None = None
