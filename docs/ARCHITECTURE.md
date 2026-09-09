# System Architecture

## Main layers

### 1. Presentation layer

- Prebuilt browser dashboard in `frontend/dist`.
- React/TypeScript development source in `frontend/src`.
- One unified chat input supports text and file attachments.
- Separate pages expose projects, HR, sales, documents, approvals, model metrics and audit logs.

### 2. API layer

FastAPI in `backend/app/main.py` exposes authentication, chat, dashboard, knowledge-base, approval, model and audit endpoints.

### 3. Identity and Zero-Trust layer

JWT identifies the current user. `RBACService` obtains roles and permissions from the enterprise dataset. Every protected tool call passes through deterministic authorization. The Security Agent can explain the decision, but the backend policy service enforces it.

### 4. Coordinator and workflow layer

The query-router model predicts a workflow ID. The Coordinator converts the workflow definition into a plan containing required agents, risk tier and approval condition. LangGraph connects the workflow nodes; a fallback path is available when LangGraph cannot be imported.

### 5. Specialized agents

| Agent | Responsibility |
|---|---|
| Coordinator | intent, workflow selection and task plan |
| Security | permission check and prompt-injection warning |
| RAG | authorized policy/report retrieval |
| HR | employees, attendance, leave and workload |
| Project | status, deadlines, tasks, risks and team allocation |
| Sales | regional/category/channel performance and approvals |
| Finance | purchase requests and expense claims |
| Monitoring | pass rate, grounding, hallucination and reliability |
| Validation | correctness/grounding/safety checks and review decision |
| Approval | creates HITL approval records |
| Explanation | reasons, sources, agents and confidence |

### 6. Data layer

Default read-only enterprise data is loaded from curated CSV files. Runtime writes are stored in SQLite:

- approval requests/decisions;
- uploaded-document metadata;
- chat/workflow records;
- audit events.

An optional PostgreSQL adapter can replace CSV reads. The source documents remain on disk.

### 7. RAG layer

The base knowledge corpus consists of 14 canonical PDFs, 14 editable DOCX files and 44 curated chunks. The default retriever is a stored TF-IDF index. Optional ChromaDB support is included. Security metadata is enforced on every retrieval.

Temporary attachments are extracted and indexed only for the current request. Authorized persistent uploads are stored under `runtime/uploads` and added to a runtime RAG index.

### 8. LLM layer

`LLM_PROVIDER=extractive` uses deterministic evidence selection and works offline. `LLM_PROVIDER=openai` sends only authorized evidence and structured agent summaries to the OpenAI Responses API, using the backend `OPENAI_API_KEY`. API failures use extractive output. See [OpenAI setup](OPENAI.md).

### 9. Validation, HITL and audit

The Validation Agent calculates correctness, grounding and safety indicators. Sensitive action workflows and low-confidence outputs create approval requests. All access decisions, uploads and approval actions are recorded in an audit store.

## Request lifecycle

```text
1. User logs in
2. User submits text and optional files
3. Files are validated and extracted
4. Coordinator predicts workflow
5. Security checks permission and injection patterns
6. Authorized agents call controlled data tools
7. RAG retrieves authorized evidence when required
8. Validator checks result quality
9. Sensitive or uncertain result is paused for HITL
10. Explanation is generated
11. Final answer, sources, confidence and traces are returned
12. Audit and workflow state are saved
```

## Why security is not delegated to an LLM

An LLM may suggest what access should be allowed, but it can hallucinate or be manipulated. The implementation uses deterministic role-permission mappings as the final enforcement boundary. Unauthorized chunks are filtered before evidence reaches the LLM.
