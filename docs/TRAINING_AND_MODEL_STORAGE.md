# Training and Model Storage Guide

## What is trained

The enterprise assistant uses several small, purpose-specific models instead of treating the LLM as the only decision maker. Security decisions are deterministic and are never delegated solely to a probabilistic model.

## 1. Query router

**Script:** `backend/scripts/train_router.py`

**Training data:**

```text
datasets/.../core/evaluation/routing_test_cases.csv
```

**Input:** natural-language enterprise request.

**Target:** one of twelve workflow IDs (`WFD001`–`WFD012`).

**Algorithm:** combined word- and character-level TF-IDF with Logistic Regression.

**Artifact:**

```text
models/router/router_model.joblib
```

**Metrics:**

```text
models/router/metrics.json
```

The artifact contains preprocessing and the classifier in one pipeline, so inference only requires `joblib.load`.

## 2. Workload classifier

**Script:** `backend/scripts/train_workload.py`

**Data:** `core/hr/employee_workload_snapshots.csv`

**Features:**

- total workload percentage;
- billable workload percentage;
- active project count;
- open task count;
- overdue task count.

**Target:** Available, Normal, High or Overloaded.

**Algorithm:** Random Forest classifier.

**Artifact:** `models/workload/workload_model.joblib`

## 3. Task delivery-risk classifier

**Script:** `backend/scripts/train_task_risk.py`

**Data:** `core/projects/tasks.csv`

**Derived features:** days to due date, overdue indicator and effort-overrun ratio.

**Target:** Low, Medium or High.

**Algorithm:** preprocessed Random Forest classifier.

**Artifact:** `models/task_risk/task_risk_model.joblib`

The labels are deterministic academic labels generated from blocked state, overdue status, progress, priority, reassignment approval and effort overrun. This must be disclosed in the report.

## 4. Sales-approval classifier

**Script:** `backend/scripts/train_sales_approval.py`

**Data:** `core/sales_finance/sales_orders.csv`

**Target:** whether discount approval is required.

**Algorithm:** numeric/categorical preprocessing plus Logistic Regression.

**Artifact:** `models/sales_approval/sales_approval_model.joblib`

## 5. HITL requirement classifier

**Script:** `backend/scripts/train_hitl.py`

**Data:** `raw_sources/agentic_ai_performance_source.csv`

**Target:** `human_intervention_required`.

**Algorithm:** preprocessed Random Forest classifier with balanced sampling.

**Artifact:** `models/hitl/hitl_model.joblib`

The actual enforcement of sensitive business actions also uses explicit workflow policy. A model cannot override the policy.

## 6. Agent-performance regressor

**Script:** `backend/scripts/train_agent_performance.py`

**Data:** `raw_sources/agentic_ai_performance_source.csv`

**Target:** `performance_index`.

**Algorithm:** preprocessed Random Forest regressor.

**Artifact:** `models/agent_performance/agent_performance_model.joblib`

## 7. Optional PyTorch neural regressor

**Script:** `backend/scripts/train_agent_performance_torch.py`

**Architecture:**

```text
Input -> Dense 128 -> BatchNorm -> Dropout
      -> Dense 64 -> Dropout
      -> Dense 32 -> Regression output
```

**Best model:**

```text
models/agent_performance_nn/best_model.pt
```

**Preprocessor:**

```text
models/agent_performance_nn/preprocessor.joblib
```

**Resume checkpoint:**

```text
runtime/checkpoints/agent_performance_nn/latest.pt
```

The checkpoint stores:

- current epoch;
- model weights;
- optimizer state;
- best validation loss;
- early-stopping counter;
- training history;
- input dimension.

### Normal training

```powershell
.\train_gpu_model.ps1 -Epochs 100 -Patience 12 -BatchSize 128 -Force -NoResume
```

### Continue after interruption

Run the same command again. The script resumes automatically when `latest.pt` exists and the final best model is not being forcibly overwritten.

### Start again from zero

```powershell
.\train_gpu_model.ps1 -Force -NoResume
```

### CPU versus GPU

The script evaluates `torch.cuda.is_available()` and automatically chooses CUDA when available. `check_gpu.py` prints the exact detected environment.

## 8. Secure RAG index

**Script:** `backend/scripts/build_rag_index.py`

**Data:** `core/rag/rag_chunks.csv`

**Default algorithm:** word/bigram TF-IDF with cosine similarity.

**Artifact:**

```text
models/rag/rag_index.joblib
```

The artifact includes:

- fitted vectorizer;
- sparse chunk matrix;
- metadata for document, section, classification, allowed roles and required permission.

Retrieval applies role and permission filters before returning evidence.

### Optional ChromaDB index

```powershell
.\setup_chroma.ps1 -Force
```

This creates a persistent Chroma collection under `runtime/chroma`. It uses deterministic local HashingVectorizer embeddings and therefore does not download an embedding model.

## Train all conventional artifacts

Skip existing files:

```powershell
.\train_models.ps1
```

Force complete retraining:

```powershell
.\train_models.ps1 -Force
```

Include neural training:

```powershell
.\train_models.ps1 -Force -IncludeNeural -NeuralEpochs 100
```

## How model files are stored

Every conventional training script follows this pattern:

```python
pipeline.fit(x_train, y_train)
joblib.dump(pipeline, output_path)
```

At application startup, `backend/app/ml/registry.py` loads the artifacts lazily. If an artifact is missing, safe deterministic fallback logic keeps the application usable, but the Models dashboard shows that the artifact is unavailable.

## Artifact integrity

Run:

```powershell
.\.venv\Scripts\python.exe backend\scripts\generate_model_manifest.py
```

This creates:

```text
models/model_manifest.json
```

It records each model/metrics file, size and SHA-256 checksum.

## Evaluation

After training, `backend/scripts/evaluate_system.py` evaluates:

- router accuracy;
- secure RAG top-1 and top-3 document retrieval;
- authorization-decision accuracy.

Output:

```text
models/reports/system_evaluation.json
```

## Interpretation warning

The dataset is synthetic and intentionally includes deterministic patterns. Very high scores show that the implementation and relationships are working on this controlled academic dataset. They do not prove production generalization, fairness, security or real-world business impact.
