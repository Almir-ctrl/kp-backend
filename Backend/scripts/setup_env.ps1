param(
    [string]$EnvName = ".venv",
    [string]$Python = "python",
    [switch]$Force
)

Write-Host "Setting up Python virtual environment in: $EnvName"
if ((Test-Path $EnvName) -and (-not $Force)) {
    Write-Host "Virtual environment already exists. Use -Force to recreate." -ForegroundColor Yellow
    exit 0
}

if (Test-Path $EnvName -and $Force) {
    Remove-Item -Recurse -Force $EnvName
}

& $Python -m venv $EnvName
& "$EnvName\Scripts\Activate.ps1"
& $EnvName\Scripts\python.exe -m pip install --upgrade pip
& $EnvName\Scripts\python.exe -m pip install -r requirements-train.txt

Write-Host "Environment setup complete. Activate with:`n & $EnvName\Scripts\Activate.ps1"
