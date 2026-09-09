-- Apply once to an empty enterprise_ai schema using the Supabase SQL Editor.
-- Creates enterprise data and mutable runtime tables. Import data with load_supabase.py.
BEGIN;
CREATE SCHEMA IF NOT EXISTS enterprise_ai;
SET LOCAL search_path TO enterprise_ai, pg_catalog;

CREATE TABLE IF NOT EXISTS roles (
    role_id TEXT,
    role_name TEXT,
    description TEXT,
    risk_tier TEXT,
    PRIMARY KEY (role_id)
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_id TEXT,
    permission_name TEXT,
    description TEXT,
    PRIMARY KEY (permission_id)
);

CREATE TABLE IF NOT EXISTS departments (
    department_id TEXT,
    department_name TEXT,
    business_group TEXT,
    manager_employee_id TEXT,
    data_classification TEXT,
    active BOOLEAN,
    PRIMARY KEY (department_id)
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT,
    source_record_no BIGINT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    gender TEXT,
    email TEXT,
    country TEXT,
    work_center TEXT,
    department_id TEXT,
    department_name TEXT,
    job_title TEXT,
    manager_employee_id TEXT,
    employment_type TEXT,
    start_date DATE,
    years_at_company BIGINT,
    monthly_salary_usd NUMERIC(20,6),
    annual_salary_usd NUMERIC(20,6),
    job_rating BIGINT,
    sick_leave_days_ytd BIGINT,
    unpaid_leave_days_ytd BIGINT,
    overtime_hours_ytd BIGINT,
    baseline_workload_percent NUMERIC(20,6),
    employment_status TEXT,
    data_classification TEXT,
    source_department TEXT,
    PRIMARY KEY (employee_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT,
    employee_id TEXT,
    email TEXT,
    username TEXT,
    password_hash TEXT,
    auth_provider TEXT,
    mfa_enabled BOOLEAN,
    must_change_password BOOLEAN,
    account_status TEXT,
    created_at TIMESTAMP,
    last_login_at TIMESTAMP,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT,
    permission_id TEXT,
    role_name TEXT,
    permission_name TEXT,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id TEXT,
    role_id TEXT,
    role_name TEXT,
    assigned_at DATE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS demo_credentials (
    user_id TEXT,
    email TEXT,
    temporary_password TEXT,
    roles TEXT,
    must_change_password BOOLEAN,
    usage_note TEXT,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS employee_skills (
    employee_skill_id TEXT,
    employee_id TEXT,
    skill_name TEXT,
    proficiency_level TEXT,
    years_experience BIGINT,
    verified BOOLEAN,
    PRIMARY KEY (employee_skill_id)
);

CREATE TABLE IF NOT EXISTS attendance_summary (
    attendance_id TEXT,
    employee_id TEXT,
    period_month DATE,
    scheduled_workdays BIGINT,
    present_days BIGINT,
    remote_work_days BIGINT,
    sick_leave_days BIGINT,
    unpaid_leave_days BIGINT,
    overtime_hours NUMERIC(20,6),
    attendance_rate NUMERIC(20,6),
    PRIMARY KEY (attendance_id)
);

CREATE TABLE IF NOT EXISTS employee_workload_snapshots (
    snapshot_id TEXT,
    snapshot_date DATE,
    employee_id TEXT,
    total_workload_percent NUMERIC(20,6),
    billable_workload_percent NUMERIC(20,6),
    active_project_count BIGINT,
    open_task_count BIGINT,
    overdue_task_count BIGINT,
    workload_status TEXT,
    PRIMARY KEY (snapshot_id)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    leave_request_id TEXT,
    employee_id TEXT,
    leave_type TEXT,
    start_date DATE,
    end_date DATE,
    days_requested BIGINT,
    reason TEXT,
    status TEXT,
    approver_employee_id TEXT,
    submitted_at TIMESTAMP,
    decided_at TIMESTAMP,
    approval_required BOOLEAN,
    policy_version TEXT,
    PRIMARY KEY (leave_request_id)
);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT,
    project_name TEXT,
    description TEXT,
    business_owner_department_id TEXT,
    project_manager_employee_id TEXT,
    start_date DATE,
    planned_end_date DATE,
    current_status TEXT,
    priority TEXT,
    current_progress_percent BIGINT,
    expected_progress_percent BIGINT,
    risk_level TEXT,
    budget_usd BIGINT,
    spent_usd NUMERIC(20,6),
    data_classification TEXT,
    requires_hitl_for_changes BOOLEAN,
    created_at TIMESTAMP,
    last_reviewed_at TIMESTAMP,
    PRIMARY KEY (project_id)
);

CREATE TABLE IF NOT EXISTS project_members (
    project_member_id TEXT,
    project_id TEXT,
    employee_id TEXT,
    project_role TEXT,
    allocation_percent BIGINT,
    joined_on DATE,
    left_on TEXT,
    active BOOLEAN,
    PRIMARY KEY (project_member_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT,
    project_id TEXT,
    task_title TEXT,
    task_description TEXT,
    task_phase TEXT,
    priority TEXT,
    status TEXT,
    assigned_to_employee_id TEXT,
    created_by_employee_id TEXT,
    estimated_hours BIGINT,
    actual_hours NUMERIC(20,6),
    planned_start_date DATE,
    due_date DATE,
    completed_at TIMESTAMP,
    progress_percent BIGINT,
    blocked_reason TEXT,
    requires_approval_for_reassignment BOOLEAN,
    data_classification TEXT,
    last_updated_at TIMESTAMP,
    PRIMARY KEY (task_id)
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    dependency_id TEXT,
    project_id TEXT,
    predecessor_task_id TEXT,
    successor_task_id TEXT,
    dependency_type TEXT,
    PRIMARY KEY (dependency_id)
);

CREATE TABLE IF NOT EXISTS project_risks (
    risk_id TEXT,
    project_id TEXT,
    risk_title TEXT,
    risk_category TEXT,
    probability_score_1_5 BIGINT,
    impact_score_1_5 BIGINT,
    risk_score BIGINT,
    status TEXT,
    owner_employee_id TEXT,
    mitigation_plan TEXT,
    identified_date DATE,
    next_review_date DATE,
    PRIMARY KEY (risk_id)
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT,
    product_name TEXT,
    manufacturer TEXT,
    product_category TEXT,
    product_subcategory TEXT,
    standard_unit_cost_usd NUMERIC(20,6),
    list_price_usd NUMERIC(20,6),
    active BOOLEAN,
    launch_date DATE,
    data_classification TEXT,
    PRIMARY KEY (product_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT,
    customer_name TEXT,
    customer_segment TEXT,
    region TEXT,
    country TEXT,
    city TEXT,
    account_manager_employee_id TEXT,
    credit_limit_usd NUMERIC(20,6),
    risk_rating TEXT,
    active BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (customer_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT,
    supplier_name TEXT,
    supplier_category TEXT,
    country TEXT,
    risk_rating TEXT,
    approved BOOLEAN,
    contract_expiry_date DATE,
    data_classification TEXT,
    PRIMARY KEY (supplier_id)
);

CREATE TABLE IF NOT EXISTS sales_orders (
    order_id TEXT,
    order_date DATE,
    customer_id TEXT,
    product_id TEXT,
    account_manager_employee_id TEXT,
    order_quantity BIGINT,
    unit_cost_usd NUMERIC(20,6),
    unit_price_usd NUMERIC(20,6),
    discount_percent NUMERIC(20,6),
    cost_of_sales_usd NUMERIC(20,6),
    sales_usd NUMERIC(20,6),
    profit_usd NUMERIC(20,6),
    sales_channel TEXT,
    promotion_name TEXT,
    manufacturer TEXT,
    product_subcategory TEXT,
    product_category TEXT,
    region TEXT,
    city TEXT,
    country TEXT,
    requires_discount_approval BOOLEAN,
    required_approval_level TEXT,
    order_status TEXT,
    data_classification TEXT,
    PRIMARY KEY (order_id)
);

CREATE TABLE IF NOT EXISTS sales_targets (
    target_id TEXT,
    year BIGINT,
    month BIGINT,
    region TEXT,
    sales_target_usd NUMERIC(20,6),
    profit_margin_target_percent NUMERIC(20,6),
    PRIMARY KEY (target_id)
);

CREATE TABLE IF NOT EXISTS purchase_requests (
    purchase_request_id TEXT,
    requester_employee_id TEXT,
    department_id TEXT,
    supplier_id TEXT,
    request_title TEXT,
    business_justification TEXT,
    amount_usd NUMERIC(20,6),
    currency TEXT,
    required_approval_level TEXT,
    status TEXT,
    current_approver_employee_id TEXT,
    submitted_at TIMESTAMP,
    decided_at TIMESTAMP,
    human_approval_required BOOLEAN,
    policy_version TEXT,
    data_classification TEXT,
    PRIMARY KEY (purchase_request_id)
);

CREATE TABLE IF NOT EXISTS expense_claims (
    expense_claim_id TEXT,
    employee_id TEXT,
    department_id TEXT,
    expense_date DATE,
    expense_category TEXT,
    description TEXT,
    amount_usd NUMERIC(20,6),
    receipt_reference TEXT,
    policy_exception BOOLEAN,
    status TEXT,
    approver_employee_id TEXT,
    submitted_at TIMESTAMP,
    decided_at TIMESTAMP,
    human_approval_required BOOLEAN,
    policy_version TEXT,
    data_classification TEXT,
    PRIMARY KEY (expense_claim_id)
);

CREATE TABLE IF NOT EXISTS agent_registry (
    agent_id TEXT,
    agent_name TEXT,
    agent_type TEXT,
    description TEXT,
    framework TEXT,
    default_model TEXT,
    risk_tier TEXT,
    active BOOLEAN,
    PRIMARY KEY (agent_id)
);

CREATE TABLE IF NOT EXISTS tool_registry (
    tool_id TEXT,
    tool_name TEXT,
    description TEXT,
    required_permission TEXT,
    read_only BOOLEAN,
    high_risk BOOLEAN,
    PRIMARY KEY (tool_id)
);

CREATE TABLE IF NOT EXISTS agent_tool_permissions (
    agent_tool_permission_id TEXT,
    agent_id TEXT,
    tool_id TEXT,
    execution_mode TEXT,
    active BOOLEAN,
    PRIMARY KEY (agent_tool_permission_id)
);

CREATE TABLE IF NOT EXISTS workflow_definitions (
    workflow_definition_id TEXT,
    workflow_name TEXT,
    description TEXT,
    trigger_type TEXT,
    required_agents TEXT,
    risk_tier TEXT,
    approval_condition TEXT,
    expected_output TEXT,
    PRIMARY KEY (workflow_definition_id)
);

CREATE TABLE IF NOT EXISTS approval_requests (
    approval_request_id TEXT,
    request_type TEXT,
    business_object_type TEXT,
    business_object_id TEXT,
    requested_by_user_id TEXT,
    requested_action TEXT,
    action_payload_json JSONB,
    risk_tier TEXT,
    required_approver_roles TEXT,
    status TEXT,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP,
    policy_version TEXT,
    human_in_the_loop BOOLEAN,
    PRIMARY KEY (approval_request_id)
);

CREATE TABLE IF NOT EXISTS approval_actions (
    approval_action_id TEXT,
    approval_request_id TEXT,
    sequence_number BIGINT,
    approver_user_id TEXT,
    approver_role TEXT,
    decision TEXT,
    decision_reason TEXT,
    decided_at TIMESTAMP,
    PRIMARY KEY (approval_action_id)
);

CREATE TABLE IF NOT EXISTS access_control_decisions (
    access_decision_id TEXT,
    decision_time TIMESTAMP,
    user_id TEXT,
    assigned_roles TEXT,
    requested_permission TEXT,
    resource_type TEXT,
    resource_id TEXT,
    decision TEXT,
    decision_reason TEXT,
    policy_engine TEXT,
    zero_trust_checks TEXT,
    session_risk_score NUMERIC(20,6),
    PRIMARY KEY (access_decision_id)
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    workflow_run_id TEXT,
    workflow_definition_id TEXT,
    user_id TEXT,
    user_roles TEXT,
    original_query TEXT,
    input_modality TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,
    security_decision TEXT,
    required_permission TEXT,
    requires_human_approval BOOLEAN,
    approval_request_id TEXT,
    agent_route TEXT,
    final_answer_summary TEXT,
    evidence_sources TEXT,
    confidence_score NUMERIC(20,6),
    grounding_score NUMERIC(20,6),
    execution_time_ms BIGINT,
    estimated_cost_usd NUMERIC(20,6),
    explanation_summary TEXT,
    error_type TEXT,
    PRIMARY KEY (workflow_run_id)
);

CREATE TABLE IF NOT EXISTS agent_execution_logs (
    agent_execution_log_id TEXT,
    workflow_run_id TEXT,
    sequence_number BIGINT,
    agent_id TEXT,
    tool_id TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms BIGINT,
    input_summary TEXT,
    output_summary TEXT,
    status TEXT,
    confidence_score NUMERIC(20,6),
    input_tokens BIGINT,
    output_tokens BIGINT,
    estimated_cost_usd NUMERIC(20,6),
    error_type TEXT,
    PRIMARY KEY (agent_execution_log_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id TEXT,
    event_time TIMESTAMP,
    actor_type TEXT,
    actor_id TEXT,
    event_category TEXT,
    action TEXT,
    resource_type TEXT,
    resource_id TEXT,
    result TEXT,
    risk_tier TEXT,
    details_json JSONB,
    correlation_id TEXT,
    immutable BOOLEAN,
    PRIMARY KEY (audit_log_id)
);

CREATE TABLE IF NOT EXISTS document_catalog (
    document_id TEXT,
    document_title TEXT,
    version TEXT,
    document_owner TEXT,
    classification TEXT,
    effective_date DATE,
    allowed_roles TEXT,
    required_permission TEXT,
    canonical_pdf_path TEXT,
    editable_docx_path TEXT,
    source_type TEXT,
    active BOOLEAN,
    supersedes_document_id TEXT,
    indexing_status TEXT,
    snapshot_date DATE,
    PRIMARY KEY (document_id)
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id TEXT,
    document_id TEXT,
    document_title TEXT,
    section_number BIGINT,
    section_title TEXT,
    chunk_part BIGINT,
    chunk_text TEXT,
    classification TEXT,
    allowed_roles TEXT,
    required_permission TEXT,
    source_path TEXT,
    effective_date DATE,
    version TEXT,
    token_estimate BIGINT,
    prompt_injection_safe_handling_required BOOLEAN,
    active BOOLEAN,
    PRIMARY KEY (chunk_id)
);

CREATE TABLE IF NOT EXISTS rag_evaluation_questions (
    question_id TEXT,
    fact_id TEXT,
    question TEXT,
    user_role TEXT,
    expected_security_decision TEXT,
    expected_document_id TEXT,
    expected_answer TEXT,
    required_permission TEXT,
    expected_agent_route TEXT,
    difficulty_tier TEXT,
    input_modality TEXT,
    requires_grounding BOOLEAN,
    requires_citation BOOLEAN,
    human_review_expected BOOLEAN,
    scoring_keywords TEXT,
    PRIMARY KEY (question_id)
);

CREATE TABLE IF NOT EXISTS prompt_injection_tests (
    test_id TEXT,
    input_modality TEXT,
    malicious_instruction TEXT,
    user_role TEXT,
    target_resource TEXT,
    expected_behavior TEXT,
    expected_security_decision TEXT,
    expected_audit_event TEXT,
    requires_human_review BOOLEAN,
    policy_document_id TEXT,
    PRIMARY KEY (test_id)
);

CREATE TABLE IF NOT EXISTS evaluation_programs (
    program_id TEXT,
    program_name TEXT,
    agent_system_name TEXT,
    workflow_definition_id TEXT,
    primary_use_case TEXT,
    owning_team TEXT,
    candidate_model_name TEXT,
    baseline_model_name TEXT,
    risk_tier TEXT,
    created_at DATE,
    status TEXT,
    PRIMARY KEY (program_id)
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    eval_run_id TEXT,
    program_id TEXT,
    run_started_at TIMESTAMP,
    eval_batch_name TEXT,
    candidate_variant TEXT,
    items_total BIGINT,
    avg_judge_score NUMERIC(20,6),
    pass_rate NUMERIC(20,6),
    review_rate NUMERIC(20,6),
    cost_usd NUMERIC(20,6),
    dataset_split TEXT,
    PRIMARY KEY (eval_run_id)
);

CREATE TABLE IF NOT EXISTS evaluation_items (
    eval_item_id TEXT,
    eval_run_id TEXT,
    program_id TEXT,
    scenario_id TEXT,
    task_category TEXT,
    difficulty_tier TEXT,
    input_modality TEXT,
    requires_tool_use BOOLEAN,
    requires_grounding BOOLEAN,
    policy_sensitivity TEXT,
    input_text TEXT,
    expected_workflow_definition_id TEXT,
    PRIMARY KEY (eval_item_id)
);

CREATE TABLE IF NOT EXISTS judge_results (
    judge_result_id TEXT,
    eval_item_id TEXT,
    eval_run_id TEXT,
    judge_type TEXT,
    overall_score NUMERIC(20,6),
    correctness_score NUMERIC(20,6),
    grounding_score NUMERIC(20,6),
    safety_score NUMERIC(20,6),
    routing_score NUMERIC(20,6),
    judge_label TEXT,
    error_type TEXT,
    PRIMARY KEY (judge_result_id)
);

CREATE TABLE IF NOT EXISTS reviewer_decisions (
    review_id TEXT,
    eval_item_id TEXT,
    eval_run_id TEXT,
    reviewer_role TEXT,
    review_queue TEXT,
    human_label TEXT,
    human_score NUMERIC(20,6),
    root_cause_category TEXT,
    resolution_status TEXT,
    resolution_time_min BIGINT,
    judge_human_agreement BOOLEAN,
    PRIMARY KEY (review_id)
);

CREATE TABLE IF NOT EXISTS daily_evaluation_metrics (
    metric_id TEXT,
    metric_date DATE,
    program_id TEXT,
    eval_runs_total BIGINT,
    items_total BIGINT,
    pass_rate NUMERIC(20,6),
    review_rate NUMERIC(20,6),
    regression_rate NUMERIC(20,6),
    judge_human_disagreement_rate NUMERIC(20,6),
    hallucination_rate NUMERIC(20,6),
    PRIMARY KEY (metric_id)
);

CREATE TABLE IF NOT EXISTS agent_performance_summary (
    agent_id TEXT,
    agent_name TEXT,
    executions_total BIGINT,
    success_rate NUMERIC(20,6),
    average_duration_ms NUMERIC(20,6),
    p95_duration_ms BIGINT,
    average_confidence_score NUMERIC(20,6),
    total_input_tokens BIGINT,
    total_output_tokens BIGINT,
    estimated_total_cost_usd NUMERIC(20,6),
    recovered_error_count BIGINT,
    risk_tier TEXT,
    PRIMARY KEY (agent_id)
);

CREATE TABLE IF NOT EXISTS routing_test_cases (
    routing_test_id TEXT,
    input_text TEXT,
    input_modality TEXT,
    user_role TEXT,
    expected_workflow_definition_id TEXT,
    expected_agents TEXT,
    expected_risk_tier TEXT,
    approval_rule TEXT,
    expected_output_type TEXT,
    task_category TEXT,
    PRIMARY KEY (routing_test_id)
);

CREATE TABLE IF NOT EXISTS workflow_test_cases (
    workflow_test_id TEXT,
    workflow_definition_id TEXT,
    test_name TEXT,
    user_role TEXT,
    input TEXT,
    expected_stages TEXT,
    expected_human_approval BOOLEAN,
    expected_audit_log BOOLEAN,
    expected_explanation BOOLEAN,
    expected_source_type TEXT,
    success_condition TEXT,
    PRIMARY KEY (workflow_test_id)
);

CREATE TABLE IF NOT EXISTS security_test_cases (
    security_test_id TEXT,
    user_role TEXT,
    requested_permission TEXT,
    expected_decision TEXT,
    resource_type TEXT,
    resource_classification TEXT,
    policy_engine TEXT,
    expected_reason TEXT,
    must_log_decision BOOLEAN,
    PRIMARY KEY (security_test_id)
);

CREATE TABLE IF NOT EXISTS explainability_test_cases (
    explainability_test_id TEXT,
    question_id TEXT,
    question TEXT,
    expected_components TEXT,
    must_separate_fact_and_recommendation BOOLEAN,
    must_show_approval_status BOOLEAN,
    must_not_show_private_chain_of_thought BOOLEAN,
    acceptable_explanation TEXT,
    minimum_confidence_if_auto_released NUMERIC(20,6),
    minimum_grounding_if_auto_released NUMERIC(20,6),
    PRIMARY KEY (explainability_test_id)
);

CREATE TABLE IF NOT EXISTS metrics_template (
    metric_name TEXT,
    definition TEXT,
    numerator TEXT,
    denominator TEXT,
    target TEXT,
    PRIMARY KEY (metric_name)
);

-- Foreign keys are added after all tables exist to support circular employee/department relationships.
ALTER TABLE departments ADD CONSTRAINT fk_departments_manager_employee_id_employees FOREIGN KEY (manager_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE employees ADD CONSTRAINT fk_employees_department_id_departments FOREIGN KEY (department_id) REFERENCES departments (department_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE employees ADD CONSTRAINT fk_employees_manager_employee_id_employees FOREIGN KEY (manager_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE users ADD CONSTRAINT fk_users_employee_id_employees FOREIGN KEY (employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE user_roles ADD CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY (user_id) REFERENCES users (user_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE user_roles ADD CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY (role_id) REFERENCES roles (role_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE role_permissions ADD CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY (role_id) REFERENCES roles (role_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE role_permissions ADD CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY (permission_id) REFERENCES permissions (permission_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE demo_credentials ADD CONSTRAINT fk_demo_credentials_user_id_users FOREIGN KEY (user_id) REFERENCES users (user_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE employee_skills ADD CONSTRAINT fk_employee_skills_employee_id_employees FOREIGN KEY (employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE attendance_summary ADD CONSTRAINT fk_attendance_summary_employee_id_employees FOREIGN KEY (employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE employee_workload_snapshots ADD CONSTRAINT fk_employee_workload_snapshots_employee_id_employees FOREIGN KEY (employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE leave_requests ADD CONSTRAINT fk_leave_requests_employee_id_employees FOREIGN KEY (employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE leave_requests ADD CONSTRAINT fk_leave_requests_approver_employee_id_employees FOREIGN KEY (approver_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE projects ADD CONSTRAINT fk_projects_business_owner_department_id_departments FOREIGN KEY (business_owner_department_id) REFERENCES departments (department_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE projects ADD CONSTRAINT fk_projects_project_manager_employee_id_employees FOREIGN KEY (project_manager_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE project_members ADD CONSTRAINT fk_project_members_project_id_projects FOREIGN KEY (project_id) REFERENCES projects (project_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE project_members ADD CONSTRAINT fk_project_members_employee_id_employees FOREIGN KEY (employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_project_id_projects FOREIGN KEY (project_id) REFERENCES projects (project_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_assigned_to_employee_id_employees FOREIGN KEY (assigned_to_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_created_by_employee_id_employees FOREIGN KEY (created_by_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE task_dependencies ADD CONSTRAINT fk_task_dependencies_project_id_projects FOREIGN KEY (project_id) REFERENCES projects (project_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE task_dependencies ADD CONSTRAINT fk_task_dependencies_predecessor_task_id_tasks FOREIGN KEY (predecessor_task_id) REFERENCES tasks (task_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE task_dependencies ADD CONSTRAINT fk_task_dependencies_successor_task_id_tasks FOREIGN KEY (successor_task_id) REFERENCES tasks (task_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE project_risks ADD CONSTRAINT fk_project_risks_project_id_projects FOREIGN KEY (project_id) REFERENCES projects (project_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE project_risks ADD CONSTRAINT fk_project_risks_owner_employee_id_employees FOREIGN KEY (owner_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE customers ADD CONSTRAINT fk_customers_account_manager_employee_id_employees FOREIGN KEY (account_manager_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE sales_orders ADD CONSTRAINT fk_sales_orders_customer_id_customers FOREIGN KEY (customer_id) REFERENCES customers (customer_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE sales_orders ADD CONSTRAINT fk_sales_orders_product_id_products FOREIGN KEY (product_id) REFERENCES products (product_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE sales_orders ADD CONSTRAINT fk_sales_orders_account_manager_employee_id_employees FOREIGN KEY (account_manager_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE purchase_requests ADD CONSTRAINT fk_purchase_requests_requester_employee_id_employees FOREIGN KEY (requester_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE purchase_requests ADD CONSTRAINT fk_purchase_requests_department_id_departments FOREIGN KEY (department_id) REFERENCES departments (department_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE purchase_requests ADD CONSTRAINT fk_purchase_requests_supplier_id_suppliers FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE purchase_requests ADD CONSTRAINT fk_purchase_requests_current_approver_employee_id_employees FOREIGN KEY (current_approver_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE expense_claims ADD CONSTRAINT fk_expense_claims_employee_id_employees FOREIGN KEY (employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE expense_claims ADD CONSTRAINT fk_expense_claims_department_id_departments FOREIGN KEY (department_id) REFERENCES departments (department_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE expense_claims ADD CONSTRAINT fk_expense_claims_approver_employee_id_employees FOREIGN KEY (approver_employee_id) REFERENCES employees (employee_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_tool_permissions ADD CONSTRAINT fk_agent_tool_permissions_agent_id_agent_registry FOREIGN KEY (agent_id) REFERENCES agent_registry (agent_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_tool_permissions ADD CONSTRAINT fk_agent_tool_permissions_tool_id_tool_registry FOREIGN KEY (tool_id) REFERENCES tool_registry (tool_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE workflow_runs ADD CONSTRAINT fk_workflow_runs_workflow_definition_id_workflow_definitions FOREIGN KEY (workflow_definition_id) REFERENCES workflow_definitions (workflow_definition_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE workflow_runs ADD CONSTRAINT fk_workflow_runs_user_id_users FOREIGN KEY (user_id) REFERENCES users (user_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE workflow_runs ADD CONSTRAINT fk_workflow_runs_approval_request_id_approval_requests FOREIGN KEY (approval_request_id) REFERENCES approval_requests (approval_request_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_execution_logs ADD CONSTRAINT fk_agent_execution_logs_workflow_run_id_workflow_runs FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs (workflow_run_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_execution_logs ADD CONSTRAINT fk_agent_execution_logs_agent_id_agent_registry FOREIGN KEY (agent_id) REFERENCES agent_registry (agent_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_execution_logs ADD CONSTRAINT fk_agent_execution_logs_tool_id_tool_registry FOREIGN KEY (tool_id) REFERENCES tool_registry (tool_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE approval_requests ADD CONSTRAINT fk_approval_requests_requested_by_user_id_users FOREIGN KEY (requested_by_user_id) REFERENCES users (user_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE approval_actions ADD CONSTRAINT fk_approval_actions_approval_request_id_approval_requests FOREIGN KEY (approval_request_id) REFERENCES approval_requests (approval_request_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE approval_actions ADD CONSTRAINT fk_approval_actions_approver_user_id_users FOREIGN KEY (approver_user_id) REFERENCES users (user_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE access_control_decisions ADD CONSTRAINT fk_access_control_decisions_user_id_users FOREIGN KEY (user_id) REFERENCES users (user_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE rag_chunks ADD CONSTRAINT fk_rag_chunks_document_id_document_catalog FOREIGN KEY (document_id) REFERENCES document_catalog (document_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE evaluation_runs ADD CONSTRAINT fk_evaluation_runs_program_id_evaluation_programs FOREIGN KEY (program_id) REFERENCES evaluation_programs (program_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE evaluation_items ADD CONSTRAINT fk_evaluation_items_eval_run_id_evaluation_runs FOREIGN KEY (eval_run_id) REFERENCES evaluation_runs (eval_run_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE evaluation_items ADD CONSTRAINT fk_evaluation_items_program_id_evaluation_programs FOREIGN KEY (program_id) REFERENCES evaluation_programs (program_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE judge_results ADD CONSTRAINT fk_judge_results_eval_item_id_evaluation_items FOREIGN KEY (eval_item_id) REFERENCES evaluation_items (eval_item_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE judge_results ADD CONSTRAINT fk_judge_results_eval_run_id_evaluation_runs FOREIGN KEY (eval_run_id) REFERENCES evaluation_runs (eval_run_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE reviewer_decisions ADD CONSTRAINT fk_reviewer_decisions_eval_item_id_evaluation_items FOREIGN KEY (eval_item_id) REFERENCES evaluation_items (eval_item_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE reviewer_decisions ADD CONSTRAINT fk_reviewer_decisions_eval_run_id_evaluation_runs FOREIGN KEY (eval_run_id) REFERENCES evaluation_runs (eval_run_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE daily_evaluation_metrics ADD CONSTRAINT fk_daily_evaluation_metrics_program_id_evaluation_programs FOREIGN KEY (program_id) REFERENCES evaluation_programs (program_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_performance_summary ADD CONSTRAINT fk_agent_performance_summary_agent_id_agent_registry FOREIGN KEY (agent_id) REFERENCES agent_registry (agent_id) DEFERRABLE INITIALLY DEFERRED;

-- Helpful indexes for the demonstration queries.
CREATE INDEX IF NOT EXISTS idx_employees_department_id ON employees (department_id);
CREATE INDEX IF NOT EXISTS idx_employees_manager_employee_id ON employees (manager_employee_id);
CREATE INDEX IF NOT EXISTS idx_users_employee_id ON users (employee_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks (project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to_employee_id ON tasks (assigned_to_employee_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);
CREATE INDEX IF NOT EXISTS idx_project_members_project_id ON project_members (project_id);
CREATE INDEX IF NOT EXISTS idx_project_members_employee_id ON project_members (employee_id);
CREATE INDEX IF NOT EXISTS idx_sales_orders_order_date ON sales_orders (order_date);
CREATE INDEX IF NOT EXISTS idx_sales_orders_region ON sales_orders (region);
CREATE INDEX IF NOT EXISTS idx_sales_orders_product_category ON sales_orders (product_category);
CREATE INDEX IF NOT EXISTS idx_purchase_requests_status ON purchase_requests (status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id ON workflow_runs (user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs (status);
CREATE INDEX IF NOT EXISTS idx_agent_execution_logs_workflow_run_id ON agent_execution_logs (workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_access_control_decisions_user_id ON access_control_decisions (user_id);
CREATE INDEX IF NOT EXISTS idx_access_control_decisions_decision ON access_control_decisions (decision);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_time ON audit_logs (event_time);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id ON rag_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_items_eval_run_id ON evaluation_items (eval_run_id);


CREATE TABLE agentic_ai_performance_source (
	agent_id TEXT,
	agent_type TEXT,
	model_architecture TEXT,
	deployment_environment TEXT,
	task_category TEXT,
	task_complexity BIGINT,
	autonomy_level BIGINT,
	success_rate DOUBLE PRECISION,
	accuracy_score DOUBLE PRECISION,
	efficiency_score DOUBLE PRECISION,
	execution_time_seconds DOUBLE PRECISION,
	response_latency_ms DOUBLE PRECISION,
	memory_usage_mb DOUBLE PRECISION,
	cpu_usage_percent DOUBLE PRECISION,
	cost_per_task_cents DOUBLE PRECISION,
	human_intervention_required BOOLEAN,
	error_recovery_rate DOUBLE PRECISION,
	multimodal_capability BOOLEAN,
	edge_compatibility BOOLEAN,
	privacy_compliance_score DOUBLE PRECISION,
	bias_detection_score DOUBLE PRECISION,
	timestamp TEXT,
	data_quality_score DOUBLE PRECISION,
	performance_index DOUBLE PRECISION,
	cost_efficiency_ratio DOUBLE PRECISION,
	autonomous_capability_score DOUBLE PRECISION
)

;

CREATE TABLE IF NOT EXISTS runtime_approvals (
    approval_id TEXT PRIMARY KEY,
    base_approval_id TEXT,
    request_type TEXT NOT NULL,
    business_object_type TEXT NOT NULL,
    business_object_id TEXT NOT NULL,
    requested_action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    required_roles TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,
    decision_comment TEXT
);
CREATE TABLE IF NOT EXISTS uploaded_documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    classification TEXT NOT NULL,
    allowed_roles TEXT NOT NULL,
    required_permission TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    extracted_text_path TEXT NOT NULL,
    chunk_count INTEGER NOT NULL,
    uploaded_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    decision TEXT,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_history (
    chat_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    workflow_run_id TEXT NOT NULL,
    query TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS task_assignment_overrides (
    task_id TEXT PRIMARY KEY,
    original_assignee_employee_id TEXT NOT NULL,
    current_assignee_employee_id TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_approvals_status_created ON runtime_approvals (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_created ON chat_history (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_active_created ON uploaded_documents (active, created_at DESC);

-- Backend-only schema: the app authenticates users and enforces RBAC in FastAPI.
-- Do not expose this schema through the Supabase Data API.
REVOKE ALL ON SCHEMA enterprise_ai FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA enterprise_ai FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA enterprise_ai REVOKE ALL ON TABLES FROM PUBLIC;
DO $$
DECLARE
    table_record record;
    api_role text;
BEGIN
    FOR table_record IN SELECT tablename FROM pg_tables WHERE schemaname = 'enterprise_ai'
    LOOP
        EXECUTE format('ALTER TABLE enterprise_ai.%I ENABLE ROW LEVEL SECURITY', table_record.tablename);
    END LOOP;
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA enterprise_ai FROM %I', api_role);
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA enterprise_ai FROM %I', api_role);
            EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA enterprise_ai REVOKE ALL ON TABLES FROM %I', api_role);
        END IF;
    END LOOP;
END $$;
COMMIT;
