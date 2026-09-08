-- Auto-generated PostgreSQL starter schema for the NexaCore synthetic dataset.
-- Recommended import: COPY enterprise_ai.<table> FROM <csv> WITH (FORMAT csv, HEADER true, NULL '');
CREATE SCHEMA IF NOT EXISTS enterprise_ai;
SET search_path TO enterprise_ai;

CREATE TABLE IF NOT EXISTS roles (
    role_id VARCHAR(255),
    role_name VARCHAR(255),
    description VARCHAR(255),
    risk_tier VARCHAR(255),
    PRIMARY KEY (role_id)
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_id VARCHAR(255),
    permission_name VARCHAR(255),
    description VARCHAR(255),
    PRIMARY KEY (permission_id)
);

CREATE TABLE IF NOT EXISTS departments (
    department_id VARCHAR(255),
    department_name VARCHAR(255),
    business_group VARCHAR(255),
    manager_employee_id VARCHAR(255),
    data_classification VARCHAR(255),
    active BOOLEAN,
    PRIMARY KEY (department_id)
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id VARCHAR(255),
    source_record_no BIGINT,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    full_name VARCHAR(255),
    gender VARCHAR(255),
    email VARCHAR(255),
    country VARCHAR(255),
    work_center VARCHAR(255),
    department_id VARCHAR(255),
    department_name VARCHAR(255),
    job_title VARCHAR(255),
    manager_employee_id VARCHAR(255),
    employment_type VARCHAR(255),
    start_date DATE,
    years_at_company BIGINT,
    monthly_salary_usd NUMERIC(20,6),
    annual_salary_usd NUMERIC(20,6),
    job_rating BIGINT,
    sick_leave_days_ytd BIGINT,
    unpaid_leave_days_ytd BIGINT,
    overtime_hours_ytd BIGINT,
    baseline_workload_percent NUMERIC(20,6),
    employment_status VARCHAR(255),
    data_classification VARCHAR(255),
    source_department VARCHAR(255),
    PRIMARY KEY (employee_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255),
    employee_id VARCHAR(255),
    email VARCHAR(255),
    username VARCHAR(255),
    password_hash VARCHAR(255),
    auth_provider VARCHAR(255),
    mfa_enabled BOOLEAN,
    must_change_password BOOLEAN,
    account_status VARCHAR(255),
    created_at TIMESTAMP,
    last_login_at TIMESTAMP,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id VARCHAR(255),
    permission_id VARCHAR(255),
    role_name VARCHAR(255),
    permission_name VARCHAR(255),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id VARCHAR(255),
    role_id VARCHAR(255),
    role_name VARCHAR(255),
    assigned_at DATE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS demo_credentials (
    user_id VARCHAR(255),
    email VARCHAR(255),
    temporary_password VARCHAR(255),
    roles VARCHAR(255),
    must_change_password BOOLEAN,
    usage_note VARCHAR(255),
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS employee_skills (
    employee_skill_id VARCHAR(255),
    employee_id VARCHAR(255),
    skill_name VARCHAR(255),
    proficiency_level VARCHAR(255),
    years_experience BIGINT,
    verified BOOLEAN,
    PRIMARY KEY (employee_skill_id)
);

CREATE TABLE IF NOT EXISTS attendance_summary (
    attendance_id VARCHAR(255),
    employee_id VARCHAR(255),
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
    snapshot_id VARCHAR(255),
    snapshot_date DATE,
    employee_id VARCHAR(255),
    total_workload_percent NUMERIC(20,6),
    billable_workload_percent NUMERIC(20,6),
    active_project_count BIGINT,
    open_task_count BIGINT,
    overdue_task_count BIGINT,
    workload_status VARCHAR(255),
    PRIMARY KEY (snapshot_id)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    leave_request_id VARCHAR(255),
    employee_id VARCHAR(255),
    leave_type VARCHAR(255),
    start_date DATE,
    end_date DATE,
    days_requested BIGINT,
    reason VARCHAR(255),
    status VARCHAR(255),
    approver_employee_id VARCHAR(255),
    submitted_at TIMESTAMP,
    decided_at TIMESTAMP,
    approval_required BOOLEAN,
    policy_version VARCHAR(255),
    PRIMARY KEY (leave_request_id)
);

CREATE TABLE IF NOT EXISTS projects (
    project_id VARCHAR(255),
    project_name VARCHAR(255),
    description VARCHAR(255),
    business_owner_department_id VARCHAR(255),
    project_manager_employee_id VARCHAR(255),
    start_date DATE,
    planned_end_date DATE,
    current_status VARCHAR(255),
    priority VARCHAR(255),
    current_progress_percent BIGINT,
    expected_progress_percent BIGINT,
    risk_level VARCHAR(255),
    budget_usd BIGINT,
    spent_usd NUMERIC(20,6),
    data_classification VARCHAR(255),
    requires_hitl_for_changes BOOLEAN,
    created_at TIMESTAMP,
    last_reviewed_at TIMESTAMP,
    PRIMARY KEY (project_id)
);

CREATE TABLE IF NOT EXISTS project_members (
    project_member_id VARCHAR(255),
    project_id VARCHAR(255),
    employee_id VARCHAR(255),
    project_role VARCHAR(255),
    allocation_percent BIGINT,
    joined_on DATE,
    left_on TEXT,
    active BOOLEAN,
    PRIMARY KEY (project_member_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(255),
    project_id VARCHAR(255),
    task_title VARCHAR(255),
    task_description VARCHAR(255),
    task_phase VARCHAR(255),
    priority VARCHAR(255),
    status VARCHAR(255),
    assigned_to_employee_id VARCHAR(255),
    created_by_employee_id VARCHAR(255),
    estimated_hours BIGINT,
    actual_hours NUMERIC(20,6),
    planned_start_date DATE,
    due_date DATE,
    completed_at TIMESTAMP,
    progress_percent BIGINT,
    blocked_reason VARCHAR(255),
    requires_approval_for_reassignment BOOLEAN,
    data_classification VARCHAR(255),
    last_updated_at TIMESTAMP,
    PRIMARY KEY (task_id)
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    dependency_id VARCHAR(255),
    project_id VARCHAR(255),
    predecessor_task_id VARCHAR(255),
    successor_task_id VARCHAR(255),
    dependency_type VARCHAR(255),
    PRIMARY KEY (dependency_id)
);

CREATE TABLE IF NOT EXISTS project_risks (
    risk_id VARCHAR(255),
    project_id VARCHAR(255),
    risk_title VARCHAR(255),
    risk_category VARCHAR(255),
    probability_score_1_5 BIGINT,
    impact_score_1_5 BIGINT,
    risk_score BIGINT,
    status VARCHAR(255),
    owner_employee_id VARCHAR(255),
    mitigation_plan VARCHAR(255),
    identified_date DATE,
    next_review_date DATE,
    PRIMARY KEY (risk_id)
);

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(255),
    product_name VARCHAR(255),
    manufacturer VARCHAR(255),
    product_category VARCHAR(255),
    product_subcategory VARCHAR(255),
    standard_unit_cost_usd NUMERIC(20,6),
    list_price_usd NUMERIC(20,6),
    active BOOLEAN,
    launch_date DATE,
    data_classification VARCHAR(255),
    PRIMARY KEY (product_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(255),
    customer_name VARCHAR(255),
    customer_segment VARCHAR(255),
    region VARCHAR(255),
    country VARCHAR(255),
    city VARCHAR(255),
    account_manager_employee_id VARCHAR(255),
    credit_limit_usd NUMERIC(20,6),
    risk_rating VARCHAR(255),
    active BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (customer_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id VARCHAR(255),
    supplier_name VARCHAR(255),
    supplier_category VARCHAR(255),
    country VARCHAR(255),
    risk_rating VARCHAR(255),
    approved BOOLEAN,
    contract_expiry_date DATE,
    data_classification VARCHAR(255),
    PRIMARY KEY (supplier_id)
);

CREATE TABLE IF NOT EXISTS sales_orders (
    order_id VARCHAR(255),
    order_date DATE,
    customer_id VARCHAR(255),
    product_id VARCHAR(255),
    account_manager_employee_id VARCHAR(255),
    order_quantity BIGINT,
    unit_cost_usd NUMERIC(20,6),
    unit_price_usd NUMERIC(20,6),
    discount_percent NUMERIC(20,6),
    cost_of_sales_usd NUMERIC(20,6),
    sales_usd NUMERIC(20,6),
    profit_usd NUMERIC(20,6),
    sales_channel VARCHAR(255),
    promotion_name VARCHAR(255),
    manufacturer VARCHAR(255),
    product_subcategory VARCHAR(255),
    product_category VARCHAR(255),
    region VARCHAR(255),
    city VARCHAR(255),
    country VARCHAR(255),
    requires_discount_approval BOOLEAN,
    required_approval_level VARCHAR(255),
    order_status VARCHAR(255),
    data_classification VARCHAR(255),
    PRIMARY KEY (order_id)
);

CREATE TABLE IF NOT EXISTS sales_targets (
    target_id VARCHAR(255),
    year BIGINT,
    month BIGINT,
    region VARCHAR(255),
    sales_target_usd NUMERIC(20,6),
    profit_margin_target_percent NUMERIC(20,6),
    PRIMARY KEY (target_id)
);

CREATE TABLE IF NOT EXISTS purchase_requests (
    purchase_request_id VARCHAR(255),
    requester_employee_id VARCHAR(255),
    department_id VARCHAR(255),
    supplier_id VARCHAR(255),
    request_title VARCHAR(255),
    business_justification VARCHAR(255),
    amount_usd NUMERIC(20,6),
    currency VARCHAR(255),
    required_approval_level VARCHAR(255),
    status VARCHAR(255),
    current_approver_employee_id VARCHAR(255),
    submitted_at TIMESTAMP,
    decided_at TIMESTAMP,
    human_approval_required BOOLEAN,
    policy_version VARCHAR(255),
    data_classification VARCHAR(255),
    PRIMARY KEY (purchase_request_id)
);

CREATE TABLE IF NOT EXISTS expense_claims (
    expense_claim_id VARCHAR(255),
    employee_id VARCHAR(255),
    department_id VARCHAR(255),
    expense_date DATE,
    expense_category VARCHAR(255),
    description VARCHAR(255),
    amount_usd NUMERIC(20,6),
    receipt_reference VARCHAR(255),
    policy_exception BOOLEAN,
    status VARCHAR(255),
    approver_employee_id VARCHAR(255),
    submitted_at TIMESTAMP,
    decided_at TIMESTAMP,
    human_approval_required BOOLEAN,
    policy_version VARCHAR(255),
    data_classification VARCHAR(255),
    PRIMARY KEY (expense_claim_id)
);

CREATE TABLE IF NOT EXISTS agent_registry (
    agent_id VARCHAR(255),
    agent_name VARCHAR(255),
    agent_type VARCHAR(255),
    description VARCHAR(255),
    framework VARCHAR(255),
    default_model VARCHAR(255),
    risk_tier VARCHAR(255),
    active BOOLEAN,
    PRIMARY KEY (agent_id)
);

CREATE TABLE IF NOT EXISTS tool_registry (
    tool_id VARCHAR(255),
    tool_name VARCHAR(255),
    description VARCHAR(255),
    required_permission VARCHAR(255),
    read_only BOOLEAN,
    high_risk BOOLEAN,
    PRIMARY KEY (tool_id)
);

CREATE TABLE IF NOT EXISTS agent_tool_permissions (
    agent_tool_permission_id VARCHAR(255),
    agent_id VARCHAR(255),
    tool_id VARCHAR(255),
    execution_mode VARCHAR(255),
    active BOOLEAN,
    PRIMARY KEY (agent_tool_permission_id)
);

CREATE TABLE IF NOT EXISTS workflow_definitions (
    workflow_definition_id VARCHAR(255),
    workflow_name VARCHAR(255),
    description VARCHAR(255),
    trigger_type VARCHAR(255),
    required_agents VARCHAR(255),
    risk_tier VARCHAR(255),
    approval_condition VARCHAR(255),
    expected_output VARCHAR(255),
    PRIMARY KEY (workflow_definition_id)
);

CREATE TABLE IF NOT EXISTS approval_requests (
    approval_request_id VARCHAR(255),
    request_type VARCHAR(255),
    business_object_type VARCHAR(255),
    business_object_id VARCHAR(255),
    requested_by_user_id VARCHAR(255),
    requested_action VARCHAR(255),
    action_payload_json JSONB,
    risk_tier VARCHAR(255),
    required_approver_roles VARCHAR(255),
    status VARCHAR(255),
    created_at TIMESTAMP,
    resolved_at TIMESTAMP,
    policy_version VARCHAR(255),
    human_in_the_loop BOOLEAN,
    PRIMARY KEY (approval_request_id)
);

CREATE TABLE IF NOT EXISTS approval_actions (
    approval_action_id VARCHAR(255),
    approval_request_id VARCHAR(255),
    sequence_number BIGINT,
    approver_user_id VARCHAR(255),
    approver_role VARCHAR(255),
    decision VARCHAR(255),
    decision_reason VARCHAR(255),
    decided_at TIMESTAMP,
    PRIMARY KEY (approval_action_id)
);

CREATE TABLE IF NOT EXISTS access_control_decisions (
    access_decision_id VARCHAR(255),
    decision_time TIMESTAMP,
    user_id VARCHAR(255),
    assigned_roles VARCHAR(255),
    requested_permission VARCHAR(255),
    resource_type VARCHAR(255),
    resource_id VARCHAR(255),
    decision VARCHAR(255),
    decision_reason VARCHAR(255),
    policy_engine VARCHAR(255),
    zero_trust_checks VARCHAR(255),
    session_risk_score NUMERIC(20,6),
    PRIMARY KEY (access_decision_id)
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    workflow_run_id VARCHAR(255),
    workflow_definition_id VARCHAR(255),
    user_id VARCHAR(255),
    user_roles VARCHAR(255),
    original_query VARCHAR(255),
    input_modality VARCHAR(255),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(255),
    security_decision VARCHAR(255),
    required_permission VARCHAR(255),
    requires_human_approval BOOLEAN,
    approval_request_id VARCHAR(255),
    agent_route VARCHAR(255),
    final_answer_summary VARCHAR(255),
    evidence_sources VARCHAR(255),
    confidence_score NUMERIC(20,6),
    grounding_score NUMERIC(20,6),
    execution_time_ms BIGINT,
    estimated_cost_usd NUMERIC(20,6),
    explanation_summary VARCHAR(255),
    error_type VARCHAR(255),
    PRIMARY KEY (workflow_run_id)
);

CREATE TABLE IF NOT EXISTS agent_execution_logs (
    agent_execution_log_id VARCHAR(255),
    workflow_run_id VARCHAR(255),
    sequence_number BIGINT,
    agent_id VARCHAR(255),
    tool_id VARCHAR(255),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms BIGINT,
    input_summary VARCHAR(255),
    output_summary VARCHAR(255),
    status VARCHAR(255),
    confidence_score NUMERIC(20,6),
    input_tokens BIGINT,
    output_tokens BIGINT,
    estimated_cost_usd NUMERIC(20,6),
    error_type VARCHAR(255),
    PRIMARY KEY (agent_execution_log_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id VARCHAR(255),
    event_time TIMESTAMP,
    actor_type VARCHAR(255),
    actor_id VARCHAR(255),
    event_category VARCHAR(255),
    action VARCHAR(255),
    resource_type VARCHAR(255),
    resource_id VARCHAR(255),
    result VARCHAR(255),
    risk_tier VARCHAR(255),
    details_json JSONB,
    correlation_id VARCHAR(255),
    immutable BOOLEAN,
    PRIMARY KEY (audit_log_id)
);

CREATE TABLE IF NOT EXISTS document_catalog (
    document_id VARCHAR(255),
    document_title VARCHAR(255),
    version VARCHAR(255),
    document_owner VARCHAR(255),
    classification VARCHAR(255),
    effective_date DATE,
    allowed_roles VARCHAR(255),
    required_permission VARCHAR(255),
    canonical_pdf_path VARCHAR(255),
    editable_docx_path VARCHAR(255),
    source_type VARCHAR(255),
    active BOOLEAN,
    supersedes_document_id TEXT,
    indexing_status VARCHAR(255),
    snapshot_date DATE,
    PRIMARY KEY (document_id)
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id VARCHAR(255),
    document_id VARCHAR(255),
    document_title VARCHAR(255),
    section_number BIGINT,
    section_title VARCHAR(255),
    chunk_part BIGINT,
    chunk_text TEXT,
    classification VARCHAR(255),
    allowed_roles VARCHAR(255),
    required_permission VARCHAR(255),
    source_path VARCHAR(255),
    effective_date DATE,
    version VARCHAR(255),
    token_estimate BIGINT,
    prompt_injection_safe_handling_required BOOLEAN,
    active BOOLEAN,
    PRIMARY KEY (chunk_id)
);

CREATE TABLE IF NOT EXISTS rag_evaluation_questions (
    question_id VARCHAR(255),
    fact_id VARCHAR(255),
    question VARCHAR(255),
    user_role VARCHAR(255),
    expected_security_decision VARCHAR(255),
    expected_document_id VARCHAR(255),
    expected_answer VARCHAR(255),
    required_permission VARCHAR(255),
    expected_agent_route VARCHAR(255),
    difficulty_tier VARCHAR(255),
    input_modality VARCHAR(255),
    requires_grounding BOOLEAN,
    requires_citation BOOLEAN,
    human_review_expected BOOLEAN,
    scoring_keywords VARCHAR(255),
    PRIMARY KEY (question_id)
);

CREATE TABLE IF NOT EXISTS prompt_injection_tests (
    test_id VARCHAR(255),
    input_modality VARCHAR(255),
    malicious_instruction VARCHAR(255),
    user_role VARCHAR(255),
    target_resource VARCHAR(255),
    expected_behavior VARCHAR(255),
    expected_security_decision VARCHAR(255),
    expected_audit_event VARCHAR(255),
    requires_human_review BOOLEAN,
    policy_document_id VARCHAR(255),
    PRIMARY KEY (test_id)
);

CREATE TABLE IF NOT EXISTS evaluation_programs (
    program_id VARCHAR(255),
    program_name VARCHAR(255),
    agent_system_name VARCHAR(255),
    workflow_definition_id VARCHAR(255),
    primary_use_case VARCHAR(255),
    owning_team VARCHAR(255),
    candidate_model_name VARCHAR(255),
    baseline_model_name VARCHAR(255),
    risk_tier VARCHAR(255),
    created_at DATE,
    status VARCHAR(255),
    PRIMARY KEY (program_id)
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    eval_run_id VARCHAR(255),
    program_id VARCHAR(255),
    run_started_at TIMESTAMP,
    eval_batch_name VARCHAR(255),
    candidate_variant VARCHAR(255),
    items_total BIGINT,
    avg_judge_score NUMERIC(20,6),
    pass_rate NUMERIC(20,6),
    review_rate NUMERIC(20,6),
    cost_usd NUMERIC(20,6),
    dataset_split VARCHAR(255),
    PRIMARY KEY (eval_run_id)
);

CREATE TABLE IF NOT EXISTS evaluation_items (
    eval_item_id VARCHAR(255),
    eval_run_id VARCHAR(255),
    program_id VARCHAR(255),
    scenario_id VARCHAR(255),
    task_category VARCHAR(255),
    difficulty_tier VARCHAR(255),
    input_modality VARCHAR(255),
    requires_tool_use BOOLEAN,
    requires_grounding BOOLEAN,
    policy_sensitivity VARCHAR(255),
    input_text VARCHAR(255),
    expected_workflow_definition_id VARCHAR(255),
    PRIMARY KEY (eval_item_id)
);

CREATE TABLE IF NOT EXISTS judge_results (
    judge_result_id VARCHAR(255),
    eval_item_id VARCHAR(255),
    eval_run_id VARCHAR(255),
    judge_type VARCHAR(255),
    overall_score NUMERIC(20,6),
    correctness_score NUMERIC(20,6),
    grounding_score NUMERIC(20,6),
    safety_score NUMERIC(20,6),
    routing_score NUMERIC(20,6),
    judge_label VARCHAR(255),
    error_type VARCHAR(255),
    PRIMARY KEY (judge_result_id)
);

CREATE TABLE IF NOT EXISTS reviewer_decisions (
    review_id VARCHAR(255),
    eval_item_id VARCHAR(255),
    eval_run_id VARCHAR(255),
    reviewer_role VARCHAR(255),
    review_queue VARCHAR(255),
    human_label VARCHAR(255),
    human_score NUMERIC(20,6),
    root_cause_category VARCHAR(255),
    resolution_status VARCHAR(255),
    resolution_time_min BIGINT,
    judge_human_agreement BOOLEAN,
    PRIMARY KEY (review_id)
);

CREATE TABLE IF NOT EXISTS daily_evaluation_metrics (
    metric_id VARCHAR(255),
    metric_date DATE,
    program_id VARCHAR(255),
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
    agent_id VARCHAR(255),
    agent_name VARCHAR(255),
    executions_total BIGINT,
    success_rate NUMERIC(20,6),
    average_duration_ms NUMERIC(20,6),
    p95_duration_ms BIGINT,
    average_confidence_score NUMERIC(20,6),
    total_input_tokens BIGINT,
    total_output_tokens BIGINT,
    estimated_total_cost_usd NUMERIC(20,6),
    recovered_error_count BIGINT,
    risk_tier VARCHAR(255),
    PRIMARY KEY (agent_id)
);

CREATE TABLE IF NOT EXISTS routing_test_cases (
    routing_test_id VARCHAR(255),
    input_text VARCHAR(255),
    input_modality VARCHAR(255),
    user_role VARCHAR(255),
    expected_workflow_definition_id VARCHAR(255),
    expected_agents VARCHAR(255),
    expected_risk_tier VARCHAR(255),
    approval_rule VARCHAR(255),
    expected_output_type VARCHAR(255),
    task_category VARCHAR(255),
    PRIMARY KEY (routing_test_id)
);

CREATE TABLE IF NOT EXISTS workflow_test_cases (
    workflow_test_id VARCHAR(255),
    workflow_definition_id VARCHAR(255),
    test_name VARCHAR(255),
    user_role VARCHAR(255),
    input VARCHAR(255),
    expected_stages VARCHAR(255),
    expected_human_approval BOOLEAN,
    expected_audit_log BOOLEAN,
    expected_explanation BOOLEAN,
    expected_source_type VARCHAR(255),
    success_condition VARCHAR(255),
    PRIMARY KEY (workflow_test_id)
);

CREATE TABLE IF NOT EXISTS security_test_cases (
    security_test_id VARCHAR(255),
    user_role VARCHAR(255),
    requested_permission VARCHAR(255),
    expected_decision VARCHAR(255),
    resource_type VARCHAR(255),
    resource_classification VARCHAR(255),
    policy_engine VARCHAR(255),
    expected_reason VARCHAR(255),
    must_log_decision BOOLEAN,
    PRIMARY KEY (security_test_id)
);

CREATE TABLE IF NOT EXISTS explainability_test_cases (
    explainability_test_id VARCHAR(255),
    question_id VARCHAR(255),
    question VARCHAR(255),
    expected_components VARCHAR(255),
    must_separate_fact_and_recommendation BOOLEAN,
    must_show_approval_status BOOLEAN,
    must_not_show_private_chain_of_thought BOOLEAN,
    acceptable_explanation VARCHAR(255),
    minimum_confidence_if_auto_released NUMERIC(20,6),
    minimum_grounding_if_auto_released NUMERIC(20,6),
    PRIMARY KEY (explainability_test_id)
);

CREATE TABLE IF NOT EXISTS metrics_template (
    metric_name VARCHAR(255),
    definition VARCHAR(255),
    numerator VARCHAR(255),
    denominator VARCHAR(255),
    target VARCHAR(255),
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
