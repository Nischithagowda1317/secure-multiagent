param([switch]$Force)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run .\setup_and_train.ps1 first." }
& $Python -m pip install -r backend\requirements-vector.txt
$Arguments = @("backend\scripts\build_chroma_index.py")
if ($Force) { $Arguments += "--force" }
& $Python @Arguments
Write-Host "Edit .env and set RAG_BACKEND=chroma, then restart the dashboard." -ForegroundColor Green
