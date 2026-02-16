# bootstrap.ps1
$ErrorActionPreference = "Stop"

Write-Host "=== Jarvis Project Bootstrap ===" -ForegroundColor Cyan

# 1. Verify Python Version
try {
    $pyVersion = python --version 2>&1
    if ($pyVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            Write-Error "Python 3.10+ is required. Found: $pyVersion"
            exit 1
        }
        Write-Host "Found $pyVersion" -ForegroundColor Green
    } else {
        Write-Error "Could not determine Python version."
        exit 1
    }
} catch {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# 2. Create Virtual Environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Gray
}

$pythonExe = ".\.venv\Scripts\python.exe"
$pipExe = ".\.venv\Scripts\pip.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Virtual environment creation failed. $pythonExe not found."
    exit 1
}

# 3. Install Dependencies
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $pipExe install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Dependency installation failed."
    exit $LASTEXITCODE
}

# 4. Ask to Build
$response = Read-Host "Do you want to build the standalone EXE now? (Y/N)"
if ($response -match "^[Yy]") {
    Write-Host "Running build.py..." -ForegroundColor Yellow
    & $pythonExe scripts/build.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Build failed."
        exit $LASTEXITCODE
    }
}

Write-Host "`nBootstrap Complete!" -ForegroundColor Green
Write-Host "To run: .\.venv\Scripts\python.exe jarvis.py"
