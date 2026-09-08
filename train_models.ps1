param(
    [switch]$Force,
    [switch]$IncludeNeural,
    [int]$NeuralEpochs = 100
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run .\setup_and_train.ps1 first." }
$Arguments = @("backend\scripts\train_all.py")
if ($Force) { $Arguments += "--force" }
if ($IncludeNeural) {
    $Arguments += "--include-neural"
    $Arguments += "--neural-epochs"
    $Arguments += "$NeuralEpochs"
}
& $Python @Arguments
