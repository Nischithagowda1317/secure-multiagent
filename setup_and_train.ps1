param(
    [switch]$Force,
    [switch]$IncludeNeural,
    [int]$NeuralEpochs = 100,
    [switch]$SkipTests,
    [switch]$BuildReact
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Step([string]$Message) {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
}

Step "1/8 - Checking Python"
if (Get-Command py -ErrorAction SilentlyContinue) {
    $SystemPython = @("py", "-3.11")
    & py -3.11 -c "import sys; print(sys.version)"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $SystemPython = @("python")
    & python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 or newer is required'; print(sys.version)"
} else {
    throw "Python was not found. Install Python 3.11 or newer and enable Add Python to PATH."
}

Step "2/8 - Creating virtual environment"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if ($SystemPython[0] -eq "py") {
        & py -3.11 -m venv .venv
    } else {
        & python -m venv .venv
    }
}
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip setuptools wheel

Step "3/8 - Installing backend dependencies"
& $Python -m pip install -r "backend\requirements.txt"

Step "4/8 - Creating local configuration"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. The default configuration runs offline." -ForegroundColor Green
} else {
    Write-Host ".env already exists; it was not overwritten." -ForegroundColor Yellow
}

Step "5/8 - Initializing the demonstration database"
$DbArguments = @("backend\scripts\init_database.py")
if ($Force) { $DbArguments += "--force" }
& $Python @DbArguments

Step "6/8 - Training models and building the secure RAG index"
$TrainArguments = @("backend\scripts\train_all.py")
if ($Force) { $TrainArguments += "--force" }
if ($IncludeNeural) {
    $TrainArguments += "--include-neural"
    $TrainArguments += "--neural-epochs"
    $TrainArguments += "$NeuralEpochs"
}
& $Python @TrainArguments

Step "7/8 - Preparing dashboard assets"
if ($BuildReact) {
    if ((Get-Command npm -ErrorAction SilentlyContinue) -and (Test-Path "frontend\package.json")) {
        Push-Location frontend
        try {
            npm install
            npm run build
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "Node/npm was not found. The supplied prebuilt dashboard will be used." -ForegroundColor Yellow
    }
} else {
    Write-Host "Using the included prebuilt dashboard. Use -BuildReact to rebuild the React source." -ForegroundColor Green
}

Step "8/8 - Validation"
& $Python "backend\scripts\validate_install.py"
& $Python "backend\scripts\smoke_test.py"
if (-not $SkipTests) {
    $env:PYTHONPATH = Join-Path $PSScriptRoot "backend"
    & $Python -m pytest -q backend\tests
}

Write-Host "`nSetup, training, model storage, and validation are complete." -ForegroundColor Green
Write-Host "Run: .\run_dashboard.ps1" -ForegroundColor Green
Write-Host "Open: http://127.0.0.1:8000" -ForegroundColor Green
