param(
    [string]$VenvPath = ".venv",
    [switch]$UpgradePip
)

Set-StrictMode -Version Latest

function Get-PipPath {
    param($venv)
    $pip = Join-Path $venv 'Scripts\pip.exe'
    if (Test-Path $pip) { return $pip }
    throw "pip not found in virtualenv at $pip"
}

try {
    $repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    Push-Location $repoRoot

    if (-not (Test-Path $VenvPath)) {
        Write-Host "Virtual environment not found at '$VenvPath'. Create one first: python -m venv $VenvPath" -ForegroundColor Yellow
        exit 1
    }

    $pip = Get-PipPath -venv $VenvPath

    if ($UpgradePip) {
        & $pip install --upgrade pip
    }

    Write-Host "Installing optional dependencies from requirements-optional.txt..."
    & $pip install -r requirements-optional.txt

    Write-Host "Optional dependencies installed."
} catch {
    Write-Error "Failed to install optional dependencies: $_"
    exit 1
} finally {
    Pop-Location
}
