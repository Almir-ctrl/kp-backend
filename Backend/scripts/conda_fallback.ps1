<#
Conda fallback helper: create a conda env (mamba preferred) from environment.yml and install audiocraft.
Usage:
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\conda_fallback.ps1 -EnvName aimusic -File ..\environment.yml
#>

param(
    [string]$EnvName = 'aimusic',
    [string]$EnvFile = '..\environment.yml'
)

function Find-Mamba {
    $m = Get-Command mamba -ErrorAction SilentlyContinue
    if ($m) { return $m.Source }
    $mm = Get-Command micromamba -ErrorAction SilentlyContinue
    if ($mm) { return $mm.Source }
    return $null
}

Write-Host "Conda fallback helper: creating conda env '$EnvName' from '$EnvFile'"
$mamba = Find-Mamba
if (-not $mamba) {
    Write-Host "mamba/micromamba not found in PATH. Please install Mambaforge and re-run this script." -ForegroundColor Yellow
    exit 2
}

if ($mamba -like '*mamba*') {
    Write-Host "Using mamba: $mamba"
    & $mamba env create -f $EnvFile -n $EnvName
} else {
    Write-Host "Using conda to create env"
    & conda env create -f $EnvFile -n $EnvName
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Conda env creation failed (exit $LASTEXITCODE). Inspect output above." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Environment '$EnvName' created. Installing pip-only extras (audiocraft)..."
& conda run -n $EnvName python -m pip install --upgrade pip setuptools wheel
& conda run -n $EnvName python -m pip install audiocraft || Write-Host "pip install audiocraft failed inside conda env; run the command manually to inspect errors." -ForegroundColor Yellow

Write-Host "Done. Activate with: mamba activate $EnvName (or conda activate $EnvName)" -ForegroundColor Green
