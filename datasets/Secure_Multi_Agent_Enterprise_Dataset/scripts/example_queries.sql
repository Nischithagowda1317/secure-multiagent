-- Run after importing the CSV files with schemas/postgres_schema.sql.
SET search_path TO enterprise_ai;

-- 1. Project Atlas status: overdue and blocked tasks.
SELECT p.project_id, p.project_name, p.current_progress_percent, p.expected_progress_percent,
       COUNT(*) FILTER (WHERE t.status <> 'Completed' AND t.due_date < DATE '2026-08-28') AS overdue_tasks,
       COUNT(*) FILTER (WHERE t.status = 'Blocked') AS blocked_tasks
FROM projects p
JOIN tasks t ON t.project_id = p.project_id
WHERE p.project_id = 'PRJ001'
GROUP BY p.project_id, p.project_name, p.current_progress_percent, p.expected_progress_percent;

-- 2. Current overloaded employees.
SELECT e.employee_id, e.full_name, e.department_name, w.total_workload_percent, w.open_task_count
FROM employee_workload_snapshots w
JOIN employees e ON e.employee_id = w.employee_id
WHERE w.snapshot_date = DATE '2026-08-28' AND w.total_workload_percent > 100
ORDER BY w.total_workload_percent DESC;

-- 3. Q2 2026 sales by region.
SELECT region, ROUND(SUM(sales_usd), 2) AS sales_usd, ROUND(SUM(profit_usd), 2) AS profit_usd
FROM sales_orders
WHERE order_date BETWEEN DATE '2026-04-01' AND DATE '2026-06-30'
  AND order_status <> 'Cancelled'
GROUP BY region
ORDER BY sales_usd DESC;

-- 4. Role-based salary permission check.
SELECT r.role_name,
       EXISTS (
         SELECT 1 FROM role_permissions rp
         JOIN permissions p ON p.permission_id = rp.permission_id
         WHERE rp.role_id = r.role_id AND p.permission_name = 'employee.salary.read'
       ) AS may_read_salary
FROM roles r
ORDER BY r.role_id;

-- 5. Secure RAG retrieval filter for an Employee role.
SELECT chunk_id, document_id, section_title, chunk_text
FROM rag_chunks
WHERE active = TRUE
  AND position('Employee' in allowed_roles) > 0
ORDER BY document_id, section_number, chunk_part;

-- 6. Human approvals still pending.
SELECT approval_request_id, request_type, business_object_id, required_approver_roles, created_at
FROM approval_requests
WHERE status = 'Pending'
ORDER BY created_at;

-- 7. Multi-agent execution trace for a workflow.
SELECT l.workflow_run_id, l.sequence_number, a.agent_name, t.tool_name, l.duration_ms, l.status
FROM agent_execution_logs l
JOIN agent_registry a ON a.agent_id = l.agent_id
JOIN tool_registry t ON t.tool_id = l.tool_id
WHERE l.workflow_run_id = 'WFR00001'
ORDER BY l.sequence_number;
