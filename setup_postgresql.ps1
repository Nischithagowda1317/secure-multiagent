param([switch]$Replace)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run .\setup_and_train.ps1 first." }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found. Install Docker Desktop or run PostgreSQL manually."
}
& docker compose up -d postgres
& $Python -m pip install -r backend\requirements-postgres.txt
$Arguments = @("backend\scripts\load_postgresql.py")
if ($Replace) { $Arguments += "--replace" }
& $Python @Arguments
Write-Host "Edit .env and set DATA_BACKEND=postgres, then restart the dashboard." -ForegroundColor Green
