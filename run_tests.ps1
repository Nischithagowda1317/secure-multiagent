$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run .\setup_and_train.ps1 first." }
$env:PYTHONPATH = Join-Path $PSScriptRoot "backend"
& $Python -m pytest -q backend\tests
& $Python backend\scripts\smoke_test.py
