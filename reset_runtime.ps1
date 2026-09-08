param([switch]$Yes)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not $Yes) {
    $answer = Read-Host "This deletes runtime approvals, uploaded documents, logs, Chroma data, and checkpoints. Type RESET"
    if ($answer -ne "RESET") { Write-Host "Cancelled."; exit 0 }
}
$targets = @(
    "runtime\assistant_runtime.db",
    "runtime\evaluation_runtime.db",
    "runtime\enterprise_data.db",
    "runtime\runtime_rag_index.joblib",
    "runtime\uploads",
    "runtime\logs",
    "runtime\checkpoints",
    "runtime\chroma"
)
foreach ($target in $targets) {
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
}
New-Item -ItemType Directory -Force runtime\uploads, runtime\logs, runtime\checkpoints, runtime\chroma | Out-Null
Write-Host "Runtime state reset. Curated datasets and trained production model files were not removed." -ForegroundColor Green
