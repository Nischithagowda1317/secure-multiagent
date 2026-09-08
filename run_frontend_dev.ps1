$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "frontend")
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm was not found. The prebuilt dashboard can still be used through run_dashboard.ps1."
}
if (-not (Test-Path "node_modules")) { npm install }
npm run dev
