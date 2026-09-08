param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\setup_and_train.ps1 first."
}
$env:PYTHONPATH = Join-Path $PSScriptRoot "backend"
$Arguments = @("-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", $HostAddress, "--port", "$Port")
if (-not $NoReload) { $Arguments += "--reload" }
Write-Host "Starting dashboard at http://$HostAddress`:$Port" -ForegroundColor Green
Write-Host "API documentation: http://$HostAddress`:$Port/docs" -ForegroundColor Green
& $Python @Arguments
