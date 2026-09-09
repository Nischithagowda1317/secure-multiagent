# Secure and Autonomous Multi-Agent Enterprise Assistant

A complete academic implementation of a secure enterprise assistant that combines:

- autonomous multi-agent workflow orchestration;
- query decomposition and agent routing;
- enterprise HR, project, sales, finance and monitoring tools;
- secure Retrieval-Augmented Generation (RAG) over PDF/DOCX knowledge documents;
- deterministic Zero-Trust Role-Based Access Control (RBAC);
- Human-in-the-Loop (HITL) approval workflows;
- explainable outputs, confidence, evidence and agent traces;
- model training, evaluation, checkpointing and artifact storage;
- a FastAPI backend and a browser dashboard;
- OpenAI API generation with an extractive fallback;
- optional PostgreSQL and ChromaDB backends.

The package is self-contained: it includes the curated datasets, generated enterprise documents, trained model artifacts, training scripts, tests, a prebuilt dashboard and full step-by-step documentation.

## Fastest Windows start

From the extracted project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_and_train.ps1
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1
```

Then open:

```text
http://127.0.0.1:8000
```

The simpler double-click route is:

```text
SETUP_AND_TRAIN.bat
RUN_DASHBOARD.bat
```

## What is already included

The ZIP already contains trained artifacts, so the first training command normally verifies and skips existing files. Use `-Force` only when you deliberately want to retrain them.

| Model/index | Purpose | Stored artifact |
|---|---|---|
| Query router | Selects the workflow and agents | `models/router/router_model.joblib` |
| Workload classifier | Classifies Available/Normal/High/Overloaded | `models/workload/workload_model.joblib` |
| Task-risk classifier | Predicts Low/Medium/High delivery risk | `models/task_risk/task_risk_model.joblib` |
| Sales approval classifier | Predicts discount approval requirement | `models/sales_approval/sales_approval_model.joblib` |
| HITL classifier | Predicts whether human intervention is required | `models/hitl/hitl_model.joblib` |
| Agent-performance regressor | Estimates agent performance index | `models/agent_performance/agent_performance_model.joblib` |
| Secure RAG index | Retrieves authorized enterprise evidence | `models/rag/rag_index.joblib` |
| Optional neural model | PyTorch agent-performance regressor | `models/agent_performance_nn/best_model.pt` |

Metrics are saved beside each model. The results are academic results on the supplied synthetic/curated datasets; they must not be presented as production validation.

## Architecture

```text
Browser Dashboard
      |
      v
FastAPI API + JWT Authentication
      |
      v
Coordinator / Router Agent
      |
      +--> Security Agent --> deterministic RBAC / Zero-Trust gate
      |
      +--> RAG Agent ------> authorized policy/report chunks
      +--> HR Agent -------> employees, workload, attendance, leave
      +--> Project Agent --> projects, tasks, risk, team allocation
      +--> Sales Agent ----> sales, products, regions, profit
      +--> Finance Agent --> purchase requests and expenses
      +--> Monitoring -----> evaluation and reliability metrics
      |
      v
Validation Agent --> HITL Approval Agent --> Explanation Agent
      |
      v
Grounded final answer + sources + confidence + audit trail
```

`LangGraph` is used when installed; the code also contains a deterministic fallback workflow so the project remains runnable in constrained environments.

## Main folders

```text
backend/app/                 FastAPI, security, services, agents and orchestration
backend/scripts/             Training, evaluation, DB/index setup and validation
backend/tests/               API, security and document tests
frontend/src/                React + TypeScript source
frontend/dist/               Ready-to-run offline dashboard served by FastAPI
datasets/                    Complete enterprise dataset and knowledge base
models/                      Trained model/index artifacts and metrics
runtime/                     SQLite state, uploads, audit events and checkpoints
docs/                        Detailed implementation and execution guides
```

## Demo credentials

All demo users use the temporary password:

```text
Demo@123!
```

Useful accounts:

| Role | Email |
|---|---|
| Employee-only (RBAC denial demo) | `rayid.zazana@nexacore.example` |
| Project Manager | `majid.aleusud@nexacore.example` |
| HR Manager | `rawan.durkzili@nexacore.example` |
| Sales Manager | `ahmad.alnajar@nexacore.example` |
| Finance Manager | `eynas.muhamad@nexacore.example` |
| Admin/Security Officer | `abd.alruhmin.alnasar@nexacore.example` |
| AI Reviewer | `ramadan.muhii.aldiyn@nexacore.example` |
| Auditor | `ranim.earabi@nexacore.example` |

These credentials are for a local academic demonstration only.

## Recommended demonstration prompts

```text
What is the remote-work policy?
```

```text
Check Project Atlas status and identify overloaded team members.
```

```text
Which region has the highest sales and profit?
```

```text
Show all employee salaries.
```

Use the last prompt with an ordinary Employee account to demonstrate access denial, then use the HR Manager account to demonstrate authorized access.

```text
Reassign a blocked Project Atlas task to an available employee.
```

This creates a Human-in-the-Loop approval request instead of silently changing enterprise data.

## Training commands

Train missing artifacts only:

```powershell
.\train_models.ps1
```

Retrain all conventional models and the RAG index:

```powershell
.\train_models.ps1 -Force
```

Train the optional neural model with checkpoint resume:

```powershell
.\train_gpu_model.ps1 -Epochs 100 -Patience 12 -BatchSize 128 -Force -NoResume
```

The neural script writes a checkpoint after every epoch. If execution stops, run the same command again and it continues from `runtime/checkpoints/agent_performance_nn/latest.pt`. Use `-NoResume` to ignore a checkpoint and `-Force` to overwrite the existing best model.

## Input support

The unified assistant input supports:

- text only;
- PDF;
- DOCX;
- TXT;
- CSV;
- XLSX;
- text plus one or more supported attachments.

An authorized administrator can also upload documents into the persistent enterprise knowledge base and rebuild the runtime RAG index.

## Default and optional operating modes

For offline operation without a server database or external model:

```text
DATA_BACKEND=csv
RAG_BACKEND=tfidf
LLM_PROVIDER=extractive
```

The configured Supabase and OpenAI setup uses:

```text
DATA_BACKEND=supabase
RAG_BACKEND=tfidf
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-openai-api-key
```

See [OpenAI setup](docs/OPENAI.md) and [Supabase setup](docs/SUPABASE.md) for credentials and startup steps.

## Detailed guides

- `docs/WINDOWS_STEP_BY_STEP.md` — complete beginner-friendly execution sequence
- `docs/TRAINING_AND_MODEL_STORAGE.md` — how every model is trained and saved
- `docs/ARCHITECTURE.md` — components and request lifecycle
- `docs/DATASET_TO_MODULE_MAPPING.md` — exact file-to-agent mapping
- `docs/API_REFERENCE.md` — endpoints and sample API calls
- `docs/DEMO_SCENARIOS.md` — college presentation scenarios
- `docs/POSTGRESQL_AND_CHROMA.md` — optional production-style backends
- `docs/REACT_DEVELOPMENT.md` — rebuild and edit the React frontend
- `docs/TROUBLESHOOTING.md` — common Windows and Python issues
- `docs/SECURITY_AND_LIMITATIONS.md` — security design and honest limitations

## Important technical scope

This project trains task-specific ML models and builds retrieval indexes. It does **not** fine-tune the weights of GPT, Llama or Mistral. Fine-tuning a large language model is unnecessary for the required demonstration. The OpenAI adapter generates natural-language answers, while enterprise facts still come from authorized tools and RAG evidence.

## Supabase PostgreSQL

See [Supabase setup](docs/SUPABASE.md) for connection settings, the
[migration SQL](supabase/migrations/202609090001_supabase_postgres.sql), and importing
existing CSV/SQLite data.
