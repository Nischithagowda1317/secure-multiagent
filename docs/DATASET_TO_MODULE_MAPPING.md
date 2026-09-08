# Dataset-to-Module Mapping

## Identity and access

| File | Used by |
|---|---|
| `users.csv` | authentication/user profile |
| `roles.csv` | role catalogue |
| `permissions.csv` | permission catalogue |
| `user_roles.csv` | user-to-role assignment |
| `role_permissions.csv` | RBAC decision engine |
| `demo_credentials.csv` | local demonstration login |
| `access_control_decisions.csv` | security dashboard/evaluation |
| `security_test_cases.csv` | authorization evaluation |

## HR Agent

| File | Purpose |
|---|---|
| `employees.csv` | employee profile, department, salary, overtime |
| `employee_skills.csv` | skill and reassignment support |
| `employee_workload_snapshots.csv` | workload classifier and overloaded staff |
| `attendance_summary.csv` | attendance and remote-work analysis |
| `leave_requests.csv` | leave status and approval workflow |

## Project Agent

| File | Purpose |
|---|---|
| `projects.csv` | status, progress, budget and risk |
| `project_members.csv` | team and allocation |
| `tasks.csv` | task status, deadline, progress and assignee |
| `task_dependencies.csv` | blocked/dependency analysis |
| `project_risks.csv` | risk register and mitigation |

## Sales and Finance Agents

| File | Purpose |
|---|---|
| `sales_orders.csv` | sales, profit, discounts and channels |
| `sales_targets.csv` | target comparison |
| `products.csv` | category and product analysis |
| `customers.csv` | region/customer context |
| `purchase_requests.csv` | finance approval workflow |
| `expense_claims.csv` | expense policy and approval |
| `suppliers.csv` | supplier risk context |

## Multi-agent orchestration

| File | Purpose |
|---|---|
| `agent_registry.csv` | available agents and default models |
| `tool_registry.csv` | controlled tools and permissions |
| `agent_tool_permissions.csv` | which agent may invoke which tool |
| `workflow_definitions.csv` | twelve workflow definitions |
| `workflow_runs.csv` | historical workflow metrics |
| `agent_execution_logs.csv` | trace and latency analysis |

## RAG Agent

| File/folder | Purpose |
|---|---|
| `document_catalog.csv` | title, classification, roles and permission |
| `rag_chunks.csv` | pre-segmented authorized knowledge text |
| `rag_evaluation_questions.csv` | expected documents and answers |
| `prompt_injection_tests.csv` | hostile document/query tests |
| `knowledge_base/canonical_pdf` | canonical PDF source documents |
| `knowledge_base/editable_docx` | editable source documents |

## HITL and audit

| File | Purpose |
|---|---|
| `approval_requests.csv` | seeded approval scenarios |
| `approval_actions.csv` | seeded decisions |
| `audit_logs.csv` | audit dashboard |
| runtime SQLite tables | new approvals, uploads and audit events |

## Evaluation and monitoring

| File | Purpose |
|---|---|
| `evaluation_programs.csv` | evaluation programme definitions |
| `evaluation_runs.csv` | run-level pass/cost measures |
| `evaluation_items.csv` | task/modality/grounding metadata |
| `judge_results.csv` | correctness, grounding, safety and errors |
| `reviewer_decisions.csv` | human-review outcomes |
| `daily_evaluation_metrics.csv` | pass, review, regression and hallucination trends |
| `routing_test_cases.csv` | router training/evaluation |
| `workflow_test_cases.csv` | end-to-end scenario expectations |
| `explainability_test_cases.csv` | explanation requirements |
| `agentic_ai_performance_source.csv` | HITL and performance model training |

## Important consistency rule

All new project functionality should use the curated files under `core`. Files under `raw_sources` are retained for provenance and selected training use; they should not replace curated relational records in the application.
