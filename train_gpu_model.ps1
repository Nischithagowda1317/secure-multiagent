param(
    [int]$Epochs = 100,
    [int]$Patience = 12,
    [int]$BatchSize = 128,
    [switch]$Force,
    [switch]$NoResume
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run .\setup_and_train.ps1 first." }

Write-Host "Checking PyTorch and CUDA..." -ForegroundColor Cyan
& $Python "backend\scripts\check_gpu.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyTorch is missing. Install the CUDA build matching your system, then rerun this script."
}

$Arguments = @(
    "backend\scripts\train_agent_performance_torch.py",
    "--epochs", "$Epochs",
    "--patience", "$Patience",
    "--batch-size", "$BatchSize"
)
if ($Force) { $Arguments += "--force" }
if ($NoResume) { $Arguments += "--no-resume" }
& $Python @Arguments
& $Python "backend\scripts\generate_model_manifest.py"

Write-Host "Best neural model: models\agent_performance_nn\best_model.pt" -ForegroundColor Green
Write-Host "Resume checkpoint: runtime\checkpoints\agent_performance_nn\latest.pt" -ForegroundColor Green
