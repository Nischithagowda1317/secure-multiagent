# Complete Windows Execution Guide

This guide assumes Windows 11, PowerShell, Python 3.11 or newer and VS Code. The dashboard can run without Node.js because a ready build is included.

## Part A — Extract and open the project

1. Download the code ZIP.
2. Right-click it and select **Extract All**.
3. Extract to a short path, for example:

```text
C:\Users\USER\Downloads\Secure_Multi_Agent_Enterprise_Assistant_Complete_Code
```

4. Do not run the project while it is still inside the ZIP.
5. Open the extracted folder.
6. Click the File Explorer address bar, type `powershell`, and press Enter.

Your prompt should now show the project folder.

## Part B — Verify Python

Run:

```powershell
py -3.11 --version
```

Expected form:

```text
Python 3.11.x
```

Python 3.12 or 3.13 may also work, but Python 3.11 is the recommended compatibility target.

When `py` is not recognized, run:

```powershell
python --version
```

When neither command works, install Python and enable **Add Python to PATH** during installation.

## Part C — One-command setup and training

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_and_train.ps1
```

The script performs these operations in order:

1. checks Python;
2. creates `.venv`;
3. upgrades pip tooling;
4. installs `backend/requirements.txt`;
5. copies `.env.example` to `.env` when `.env` is absent;
6. builds `runtime/enterprise_data.db` from the curated CSV files;
7. trains or verifies the query router;
8. trains or verifies workload prediction;
9. trains or verifies task-risk prediction;
10. trains or verifies sales-approval prediction;
11. trains or verifies HITL prediction;
12. trains or verifies agent-performance regression;
13. builds or verifies the secure RAG index;
14. evaluates routing, secure retrieval and RBAC;
15. generates the model checksum manifest;
16. validates installed modules and artifacts;
17. runs API smoke testing;
18. runs the complete automated test suite.

Because trained artifacts are included, the script skips any valid existing model. This makes setup fast and permits recovery after interruption.

## Part D — Retrain everything from the beginning

Use this only when you intentionally want new artifacts:

```powershell
.\setup_and_train.ps1 -Force
```

Or after setup:

```powershell
.\train_models.ps1 -Force
```

`-Force` overwrites the conventional `.joblib` artifacts and rebuilds the TF-IDF RAG index.

## Part E — Run the dashboard

Run:

```powershell
.\run_dashboard.ps1
```

Keep the PowerShell window open. Open:

```text
http://127.0.0.1:8000
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

Stop the server with `Ctrl+C`.

## Part F — Log in

Use:

```text
Email: majid.aleusud@nexacore.example
Password: Demo@123!
```

This user has Employee and Project Manager roles.

The Login page also calls `/api/auth/demo-accounts` and shows available demo users.

## Part G — Test the main project requirements

### 1. RAG and source grounding

Ask:

```text
What is the remote-work policy?
```

Expected behavior:

- Coordinator chooses the knowledge workflow.
- Security checks `document.read_public`.
- RAG searches authorized chunks.
- The answer states the allowed remote-work limit and manager approval rule.
- The source includes the Remote Work policy.
- Validation and explanation are shown.

### 2. Multi-agent collaboration

Ask:

```text
Check Project Atlas status and identify overloaded team members.
```

Expected result includes:

- 58% current progress versus 78% expected;
- six overdue unfinished tasks;
- two blocked tasks;
- two overloaded members at 125% and 112%;
- Project Agent and HR Agent traces;
- evidence and confidence.

### 3. Zero-Trust/RBAC

Log in with the ordinary Employee account `rayid.zazana@nexacore.example` using `Demo@123!`, and ask:

```text
Show all employee salaries.
```

Expected output is **Access Denied**.

Log in with the HR Manager account:

```text
rawan.durkzili@nexacore.example
Demo@123!
```

Repeat the request to demonstrate authorized access.

### 4. Human-in-the-Loop

Ask as a Project Manager:

```text
Reassign a blocked Project Atlas task to an available employee.
```

The system should create an approval request and return **Awaiting Approval**. Open the Approvals page, review the evidence, and approve or reject the request with an eligible role.

### 5. File input

On the Assistant page, attach one of these:

```text
datasets\Secure_Multi_Agent_Enterprise_Dataset\knowledge_base\canonical_pdf\DOC012_Project_Atlas_Status_Report.pdf
```

Then ask:

```text
Summarize the attached report and compare it with the project database.
```

The system extracts the attachment, creates temporary session chunks, runs RAG and combines the document evidence with structured project data.

## Part H — Train the optional neural model

The regular system does not require a GPU. To demonstrate neural training:

1. Complete normal setup.
2. Install a CUDA-enabled PyTorch build that matches your NVIDIA driver/CUDA environment.
3. Verify:

```powershell
.\.venv\Scripts\python.exe backend\scripts\check_gpu.py
```

Look for:

```json
"cuda_available": true
```

4. Train:

```powershell
.\train_gpu_model.ps1 -Epochs 100 -Patience 12 -BatchSize 128 -Force -NoResume
```

Artifacts:

```text
models\agent_performance_nn\best_model.pt
models\agent_performance_nn\preprocessor.joblib
models\agent_performance_nn\metrics.json
models\agent_performance_nn\config.json
runtime\checkpoints\agent_performance_nn\latest.pt
```

The script uses:

- validation monitoring after every epoch;
- best-model checkpointing;
- latest-state checkpointing;
- early stopping;
- automatic CUDA selection;
- resume after interruption.

When training is interrupted, run the same command again. Do not add `-Force`; it reads `latest.pt` and continues.

## Part I — Rebuild the React frontend

The included static dashboard is immediately usable. To edit/build the React source:

1. Install Node.js.
2. Run the backend in one terminal:

```powershell
.\run_dashboard.ps1
```

3. Run the frontend development server in a second terminal:

```powershell
.\run_frontend_dev.ps1
```

4. Open:

```text
http://127.0.0.1:5173
```

To create a production build:

```powershell
cd frontend
npm install
npm run build
cd ..
```

The build is written to `frontend/dist` and FastAPI serves it automatically.

## Part J — Optional PostgreSQL and ChromaDB

The default CSV + SQLite + TF-IDF mode is sufficient for the complete academic demonstration. For optional backends see `POSTGRESQL_AND_CHROMA.md`.

## Part K — Run tests again

```powershell
.\run_tests.ps1
```

## Part L — Reset runtime state

This removes runtime approvals, uploads, logs, checkpoints and optional Chroma data, but does not remove the source datasets or conventional trained models:

```powershell
.\reset_runtime.ps1
```

Type `RESET` when asked.
