# Final Demonstration Scenarios

## Scenario 1 — RAG policy question

**Role:** Employee

**Input:**

```text
What is the remote-work policy?
```

**Expected path:** Coordinator -> Security -> RAG -> Validation -> Explanation.

**Expected evidence:** `DOC003_Remote_Work_and_Flexible_Hours_Policy.pdf`.

**What it proves:** grounded enterprise retrieval, source citation, hallucination reduction and role-aware document access.

## Scenario 2 — Multi-agent project analysis

**Role:** Project Manager

**Input:**

```text
Check Project Atlas status and identify overloaded team members.
```

**Expected path:** Coordinator -> Security -> Project Agent + HR Agent + RAG -> Validation -> Explanation.

**Expected facts:**

- current progress 58%;
- expected progress 78%;
- six overdue unfinished tasks;
- two blocked tasks;
- overloaded workload values 125% and 112%.

**What it proves:** intelligent routing, structured tools, multi-agent collaboration and explainability.

## Scenario 3 — Role-based denial

**Role:** ordinary Employee

**Input:**

```text
Show all employee salaries.
```

**Expected:** access denied before salary data reaches answer generation.

**What it proves:** Zero-Trust security and RBAC are enforced outside the LLM.

## Scenario 4 — Authorized HR analysis

**Role:** HR Manager

**Input:**

```text
Show salary and overtime information for the highest-overtime employees.
```

**Expected:** permitted HR data, source trace and audit event.

**What it proves:** the system does not simply block sensitive data; it permits legitimate authorized use.

## Scenario 5 — Sales analysis

**Role:** Sales Manager

**Input:**

```text
Which region and product category have the highest sales and profit?
```

**Expected path:** Coordinator -> Security -> Sales Agent -> Validation -> Explanation.

**What it proves:** analytics over structured enterprise records.

## Scenario 6 — HITL action

**Role:** Project Manager

**Input:**

```text
Reassign a blocked Project Atlas task to an available employee.
```

**Expected:** approval request is created, action remains pending and an audit record is stored.

**What it proves:** autonomous planning is bounded by human authorization.

## Scenario 7 — Uploaded-document analysis

Attach `DOC012_Project_Atlas_Status_Report.pdf` and ask:

```text
Summarize this report, compare it with the project database, and recommend corrective actions.
```

**Expected:** attachment extraction, temporary RAG, Project Agent, HR Agent, combined explanation and sources.

## Scenario 8 — Agent reliability monitoring

**Role:** AI Reviewer or Admin

**Input:**

```text
Show the current agent reliability, hallucination, grounding and human-review metrics.
```

**Expected:** Monitoring Agent summarizes evaluation datasets.

## Suggested viva explanation

> The user gives one text request and may attach PDF, DOCX, CSV or XLSX files. The Coordinator predicts a workflow and decomposes the request. Deterministic RBAC verifies access before agents can read protected data. Specialized agents retrieve structured records, while the RAG agent retrieves only authorized document chunks. The Validation Agent checks quality. Sensitive actions create a Human-in-the-Loop approval instead of being executed directly. The response shows evidence, confidence, agent trace and explanation, and every important event is audited.
