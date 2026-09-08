export interface UserProfile {
  user_id: string;
  employee_id: string;
  email: string;
  username: string;
  full_name: string;
  department_name?: string;
  job_title?: string;
  roles: string[];
  permissions: string[];
  mfa_enabled: boolean;
}

export interface DemoAccount {
  user_id: string;
  email: string;
  roles: string[];
  temporary_password: string;
}

export interface SourceReference {
  source_id: string;
  title: string;
  source_type: string;
  section?: string;
  path?: string;
  score?: number;
}

export interface AgentTrace {
  sequence: number;
  agent_id: string;
  agent_name: string;
  status: string;
  duration_ms: number;
  summary: string;
  confidence: number;
}

export interface ChatResponse {
  workflow_run_id: string;
  workflow_id: string;
  workflow_name: string;
  status: string;
  answer: string;
  sections: Array<Record<string, unknown>>;
  security: {
    decision: string;
    permission: string;
    reason: string;
    roles: string[];
    zero_trust_checks: string[];
    session_risk_score: number;
  };
  agents: AgentTrace[];
  sources: SourceReference[];
  confidence: number;
  grounding_score: number;
  approval: {
    required: boolean;
    approval_id?: string;
    status?: string;
    required_roles: string[];
    reason?: string;
  };
  explanation: Record<string, unknown>;
  warnings: string[];
}

export type PageKey =
  | "overview"
  | "assistant"
  | "projects"
  | "hr"
  | "sales"
  | "documents"
  | "approvals"
  | "monitoring"
  | "models"
  | "audit";
