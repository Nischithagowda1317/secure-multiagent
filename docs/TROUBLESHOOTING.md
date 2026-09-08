# Troubleshooting

## PowerShell says scripts are disabled

Run in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then run the script again.

## `py -3.11` is not recognized

Try:

```powershell
python --version
```

Install Python 3.11+ and enable **Add Python to PATH** when neither command works.

## `No module named ...`

Make sure commands use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Then rerun setup.

## Port 8000 is already in use

Run on a different port:

```powershell
.\run_dashboard.ps1 -Port 8010
```

Open `http://127.0.0.1:8010`.

## Dashboard loads but API calls fail

Check:

```text
http://127.0.0.1:8000/api/health
```

When it does not return JSON, inspect the PowerShell server error. Also verify `.env` has valid backend values.

## A model file is missing

Run:

```powershell
.\train_models.ps1
```

Force recreation:

```powershell
.\train_models.ps1 -Force
```

## GPU script reports `cuda_available: false`

A generic `pip install torch` may install a CPU build. Install a CUDA-enabled PyTorch package compatible with your NVIDIA driver, then verify with:

```powershell
.\.venv\Scripts\python.exe backend\scripts\check_gpu.py
```

The application itself still runs without CUDA.

## Neural training stopped midway

Run the same `train_gpu_model.ps1` command again without `-Force` and without `-NoResume`. It resumes from:

```text
runtime\checkpoints\agent_performance_nn\latest.pt
```

## PostgreSQL connection refused

Check:

```powershell
docker compose ps
```

Start:

```powershell
docker compose up -d postgres
```

Then rerun:

```powershell
.\setup_postgresql.ps1 -Replace
```

Use `DATA_BACKEND=csv` to return to zero-setup mode.

## Chroma selected but retrieval seems unchanged

Rebuild:

```powershell
.\setup_chroma.ps1 -Force
```

Confirm `.env` contains `RAG_BACKEND=chroma`, stop the server and start it again.

## File upload rejected

Supported extensions:

```text
.pdf .docx .txt .csv .xlsx
```

Default maximum size is 10 MB. Change `MAX_UPLOAD_MB` in `.env` when necessary.

## Login fails

Use the exact local demo password:

```text
Demo@123!
```

Retrieve current demo accounts from:

```text
http://127.0.0.1:8000/api/auth/demo-accounts
```

## Tests

Run:

```powershell
.\run_tests.ps1
```

For a complete reinstall, remove `.venv` and run `setup_and_train.ps1` again. Do not delete the datasets or models folders unless you intend to recreate their contents.
