# Secure Multi-Agent Enterprise Assistant - Complete Dataset Package

## Overview

This package is an implementation-ready, internally consistent dataset for the project **Secure and Autonomous Multi-Agent Enterprise Assistant**. It combines the useful uploaded datasets with a new synthetic enterprise data model so the full project can demonstrate:

- Multi-agent task planning and tool routing
- Enterprise HR, project, sales, and finance analysis
- Retrieval-Augmented Generation (RAG) over PDF and DOCX documents
- Zero-Trust authorization and Role-Based Access Control (RBAC)
- Human-in-the-Loop (HITL) approvals
- Explainable AI and complete audit trails
- Agent reliability, grounding, hallucination, safety, cost, and performance evaluation

The generated company is fictional and is called **NexaCore Technologies**. The dataset snapshot date is **2026-08-28**.

## Package summary

The curated `core/` area contains **50 CSV tables** and more than **20,000 linked records**. Important quantities include:

| Area | Included data |
|---|---:|
| Departments | 12 |
| Employees and users | 200 each |
| Roles and permissions | 10 roles, 32 permissions |
| Employee skills | 600 |
| Attendance summaries | 2,400 |
| Workload snapshots | 800 |
| Leave requests | 160 |
| Projects | 18 |
| Project members | 197 |
| Tasks | 539 |
| Sales orders | 5,000 |
| Customers and products | 250 customers, 60 products |
| Purchase requests and expenses | 180 purchases, 260 expense claims |
| AI agents and tools | 11 agents, 20 controlled tools |
| Workflow definitions and runs | 12 definitions, 400 runs |
| Agent execution events | 1,569 |
| HITL approval requests | 200 |
| Access-control decisions | 700 |
| Audit events | 1,300 |
| Enterprise knowledge documents | 14 DOCX + 14 canonical PDF files |
| RAG chunks and gold questions | 44 chunks, 160 questions |
| Prompt-injection tests | 60 |
| Security test matrix | 320 role-permission cases |
| Routing and workflow tests | 120 routing + 96 end-to-end cases |
| Coherent evaluation items | 960 items and 960 judge results |

## Folder structure

```text
Secure_Multi_Agent_Enterprise_Dataset/
├── README.md
├── DATA_NOTICE.md
├── generation_summary.json
├── validation_report.json
├── dataset_manifest.csv
├── checksums.sha256
├── raw_sources/
│   ├── Employees_source.xlsx
│   ├── company_sales_source.xlsx
│   ├── agentic_ai_performance_source.csv
│   └── evaluation_quality_sample/
├── core/
│   ├── identity_access/
│   ├── hr/
│   ├── projects/
│   ├── sales_finance/
│   ├── agents/
│   ├── security_audit/
│   ├── rag/
│   └── evaluation/
├── knowledge_base/
│   ├── editable_docx/
│   └── canonical_pdf/
├── schemas/
│   ├── postgres_schema.sql
│   ├── data_dictionary.csv
│   ├── relationships.md
│   └── load_order.txt
└── scripts/
    ├── validate_dataset.py
    └── example_queries.sql
```

## Which files support each project requirement?

| Project requirement | Main dataset files |
|---|---|
| User login and identity | `core/identity_access/users.csv` |
| Roles and permissions | `roles.csv`, `permissions.csv`, `user_roles.csv`, `role_permissions.csv` |
| HR Agent | `core/hr/employees.csv`, `employee_skills.csv`, `leave_requests.csv`, `employee_workload_snapshots.csv` |
| Project Agent | `core/projects/projects.csv`, `tasks.csv`, `project_members.csv`, `project_risks.csv` |
| Sales Analytics Agent | `core/sales_finance/sales_orders.csv`, `products.csv`, `customers.csv`, `sales_targets.csv` |
| Finance Agent | `purchase_requests.csv`, `expense_claims.csv`, `suppliers.csv` |
| Multi-agent orchestration | `agent_registry.csv`, `tool_registry.csv`, `workflow_definitions.csv` |
| Agent execution trace | `workflow_runs.csv`, `agent_execution_logs.csv` |
| RAG | `knowledge_base/`, `document_catalog.csv`, `rag_chunks.csv` |
| Secure RAG | Role and permission metadata in `document_catalog.csv` and `rag_chunks.csv` |
| Human-in-the-Loop | `approval_requests.csv`, `approval_actions.csv` |
| Zero-Trust testing | `access_control_decisions.csv`, `security_test_cases.csv` |
| Explainable AI | Workflow traces, source metadata, confidence fields, and `explainability_test_cases.csv` |
| Auditability | `core/security_audit/audit_logs.csv` |
| Agent evaluation | `core/evaluation/` and the preserved uploaded sample in `raw_sources/` |
| Hallucination and grounding tests | `rag_evaluation_questions.csv`, `judge_results.csv`, `daily_evaluation_metrics.csv` |
| Prompt-injection defense | `prompt_injection_tests.csv` and Security Policy `DOC005` |

## Recommended implementation path

1. Create the PostgreSQL database using `schemas/postgres_schema.sql`.
2. Import the CSV files in the order shown in `schemas/load_order.txt`. When using PostgreSQL `COPY`, treat an empty CSV value as SQL `NULL`.
3. Implement authentication using `users`, `roles`, `permissions`, `user_roles`, and `role_permissions`.
4. Build deterministic backend authorization. Do not rely on an LLM as the final permission checker.
5. Implement HR, Project, Sales, and Finance tools over the related tables.
6. Create the agent graph using `agent_registry`, `tool_registry`, and `workflow_definitions`.
7. For RAG, ingest either the canonical PDFs or the supplied `rag_chunks.csv`. Do not index both versions at the same time, or retrieval results may be duplicated.
8. Apply the `allowed_roles` and `required_permission` filters before any retrieved chunk is sent to the LLM.
9. Use `approval_requests` and `approval_actions` to pause high-risk workflows until a human decides.
10. Evaluate the system with the gold RAG questions, RBAC matrix, workflow tests, injection tests, judge results, and metrics template.

## Demonstration facts intentionally built into the data

These facts are deterministic so you can test expected output:

- Project Atlas is **At Risk**, with **58% current progress versus 78% expected progress**.
- Project Atlas has exactly **6 overdue unfinished tasks** and **2 blocked tasks** on 2026-08-28.
- Atlas team members Alaa Altahhan and Ranim Earabi have current workloads of **125%** and **112%**.
- Project Nova is **On Track**, with **82% progress versus 80% expected**, **1 overdue unfinished task**, and **0 blocked tasks**.
- The standard leave policy provides **12 casual**, **10 sick**, and **18 annual** leave days.
- The standard remote-work allowance is **up to 2 days per week with manager approval**.
- Salary data requires `employee.salary.read`; an ordinary Employee or Project Manager is not allowed to read another employee's salary.
- AI output requires human review when confidence is below **0.75** or grounding is below **0.80**.
- Security incident response targets are P1 **15 minutes**, P2 **30 minutes**, P3 **4 business hours**, and P4 **1 business day**.

## Demo credentials

`core/identity_access/demo_credentials.csv` contains one synthetic demonstration account for each major role. The temporary local-demo password is:

```text
Demo@123!
```

These credentials are only for local demonstration. Do not reuse them in a deployed application, and do not import `demo_credentials.csv` into production.

## Uploaded datasets versus generated datasets

The package preserves the useful uploaded files under `raw_sources/`:

- Employee Excel source
- Company sales Excel source
- One copy of the agent-performance CSV
- The original free evaluation-quality sample and notebook

The two uploaded agent-performance CSVs were identical, so only one copy is included. The original evaluation sample is preserved unchanged, but its IDs should not be treated as the core relational model. A new coherent and fully linked evaluation package is available under `core/evaluation/`.

## Validation

Run:

```bash
python scripts/validate_dataset.py
```

The validator checks CSV presence, primary-key uniqueness, key foreign-key relationships, PDF/DOCX availability, the complete RBAC test matrix, and deterministic Atlas/Nova facts.

Example SQL queries are provided in `scripts/example_queries.sql`.

## Important limitation

The HR, sales, project, financial, AI, and policy records in the curated package are synthetic. They are suitable for system development, academic demonstration, testing, and evaluation, but not for making decisions about real employees, customers, finances, or security incidents.
