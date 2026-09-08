# Dataset relationships

All operational records use synthetic IDs. The PostgreSQL schema adds foreign keys after table creation so circular manager relationships can be loaded safely.

## Main domains

- Identity and access: `users -> employees`, `user_roles -> users/roles`, and `role_permissions -> roles/permissions`.
- HR: employee skills, attendance, leave, and workload link to `employees`.
- Projects: `projects -> departments/employees`; members, tasks, dependencies, and risks link to projects.
- Sales and finance: orders link to customers, products, and account managers; purchase and expense requests link to employees, departments, and suppliers.
- Multi-agent execution: workflow runs link to workflow definitions and users; execution logs link to runs, agents, and tools.
- Security and HITL: approvals, access decisions, and audit events retain actor and resource identifiers.
- RAG: document chunks link to the document catalogue; the role and permission metadata must be applied before retrieval.
- Evaluation: programs -> runs -> items -> judge results/reviewer decisions.

## Key relationship list

- `departments.manager_employee_id` -> `employees.employee_id`
- `employees.department_id` -> `departments.department_id`
- `employees.manager_employee_id` -> `employees.employee_id`
- `users.employee_id` -> `employees.employee_id`
- `user_roles.user_id` -> `users.user_id`
- `user_roles.role_id` -> `roles.role_id`
- `role_permissions.role_id` -> `roles.role_id`
- `role_permissions.permission_id` -> `permissions.permission_id`
- `demo_credentials.user_id` -> `users.user_id`
- `employee_skills.employee_id` -> `employees.employee_id`
- `attendance_summary.employee_id` -> `employees.employee_id`
- `employee_workload_snapshots.employee_id` -> `employees.employee_id`
- `leave_requests.employee_id` -> `employees.employee_id`
- `leave_requests.approver_employee_id` -> `employees.employee_id`
- `projects.business_owner_department_id` -> `departments.department_id`
- `projects.project_manager_employee_id` -> `employees.employee_id`
- `project_members.project_id` -> `projects.project_id`
- `project_members.employee_id` -> `employees.employee_id`
- `tasks.project_id` -> `projects.project_id`
- `tasks.assigned_to_employee_id` -> `employees.employee_id`
- `tasks.created_by_employee_id` -> `employees.employee_id`
- `task_dependencies.project_id` -> `projects.project_id`
- `task_dependencies.predecessor_task_id` -> `tasks.task_id`
- `task_dependencies.successor_task_id` -> `tasks.task_id`
- `project_risks.project_id` -> `projects.project_id`
- `project_risks.owner_employee_id` -> `employees.employee_id`
- `customers.account_manager_employee_id` -> `employees.employee_id`
- `sales_orders.customer_id` -> `customers.customer_id`
- `sales_orders.product_id` -> `products.product_id`
- `sales_orders.account_manager_employee_id` -> `employees.employee_id`
- `purchase_requests.requester_employee_id` -> `employees.employee_id`
- `purchase_requests.department_id` -> `departments.department_id`
- `purchase_requests.supplier_id` -> `suppliers.supplier_id`
- `purchase_requests.current_approver_employee_id` -> `employees.employee_id`
- `expense_claims.employee_id` -> `employees.employee_id`
- `expense_claims.department_id` -> `departments.department_id`
- `expense_claims.approver_employee_id` -> `employees.employee_id`
- `agent_tool_permissions.agent_id` -> `agent_registry.agent_id`
- `agent_tool_permissions.tool_id` -> `tool_registry.tool_id`
- `workflow_runs.workflow_definition_id` -> `workflow_definitions.workflow_definition_id`
- `workflow_runs.user_id` -> `users.user_id`
- `workflow_runs.approval_request_id` -> `approval_requests.approval_request_id`
- `agent_execution_logs.workflow_run_id` -> `workflow_runs.workflow_run_id`
- `agent_execution_logs.agent_id` -> `agent_registry.agent_id`
- `agent_execution_logs.tool_id` -> `tool_registry.tool_id`
- `approval_requests.requested_by_user_id` -> `users.user_id`
- `approval_actions.approval_request_id` -> `approval_requests.approval_request_id`
- `approval_actions.approver_user_id` -> `users.user_id`
- `access_control_decisions.user_id` -> `users.user_id`
- `rag_chunks.document_id` -> `document_catalog.document_id`
- `evaluation_runs.program_id` -> `evaluation_programs.program_id`
- `evaluation_items.eval_run_id` -> `evaluation_runs.eval_run_id`
- `evaluation_items.program_id` -> `evaluation_programs.program_id`
- `judge_results.eval_item_id` -> `evaluation_items.eval_item_id`
- `judge_results.eval_run_id` -> `evaluation_runs.eval_run_id`
- `reviewer_decisions.eval_item_id` -> `evaluation_items.eval_item_id`
- `reviewer_decisions.eval_run_id` -> `evaluation_runs.eval_run_id`
- `daily_evaluation_metrics.program_id` -> `evaluation_programs.program_id`
- `agent_performance_summary.agent_id` -> `agent_registry.agent_id`
