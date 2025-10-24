<#
recreate_venv_and_install.ps1
Interactive helper to safely remove and recreate the repository `.venv`, preinstall binary wheels
for blis/thinc/spacy (when available), and optionally install `audiocraft` or the full
`requirements.txt`.

Usage (PowerShell):
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\recreate_venv_and_install.ps1 [-InstallAll]

Switches:
  -InstallAll  : After venv recreation and binary preinstalls, run `pip install -r requirements.txt`.

Behavior and safety:
 - The script searches for processes whose command lines reference the repo venv python
   path and prompts before attempting to stop them.
 - It creates the venv using the system Python (`C:\Python313\python.exe`) if present,
   otherwise `python` from PATH.
 - It upgrades pip/setuptools/wheel inside the venv.
 - It first attempts binary-only installs for blis, thinc and spacy. If that fails, it
   retries allowing source builds (requires build tools).
 - It sets CC to the short-path of LLVM clang if available to help MSVC-less builds.
 - On failure to build `blis` via pip, the script prints guidance for using conda/mamba.
#>
param(
    [switch]$InstallAll,
    [switch]$Auto,
    [switch]$NoKill,
    [string]$PythonPath = ''
)

# Hardened venv recreation script. Supports non-interactive mode (-Auto) and skipping kills (-NoKill).
$ErrorActionPreference = 'Stop'

# Compute repo root as parent of the scripts directory so venv is created at project root
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..') | Select-Object -ExpandProperty Path
Set-Location $repoRoot

$venvRel = '.venv'
$venvFull = Join-Path $repoRoot $venvRel

Write-Host "Repository root: $repoRoot" -ForegroundColor Cyan
Write-Host "Target venv: $venvRel" -ForegroundColor Cyan

function Find-VenvProcesses {
    param([string]$path)
    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.CommandLine -and ($_.CommandLine -like "*$path*" ) }
        return $procs
    } catch {
        Write-Host "Warning: could not query Win32_Process via CIM: $_" -ForegroundColor Yellow
        return @()
    }
}

# Locate processes referencing the venv python by command line
$venvPythonPattern = "\\.venv\\Scripts\\python.exe"
Write-Host "Searching for processes that reference: $venvPythonPattern" -ForegroundColor White
$found = Find-VenvProcesses -path $venvPythonPattern
if ($found -and $found.Count -gt 0) {
    Write-Host "Found processes referencing the venv python:" -ForegroundColor Yellow
    $found | Select-Object ProcessId,Name,@{N='CommandLine';E={$_.CommandLine}} | Format-Table -AutoSize
    if (-not $NoKill) {
        if ($Auto) {
            Write-Host "Auto mode: killing found processes..." -ForegroundColor Yellow
            $toKill = $found
        } else {
            $confirm = Read-Host "Kill these processes? (y/N)"
            if ($confirm -match '^[yY]') { $toKill = $found } else { $toKill = @() }
        }
        foreach ($p in $toKill) {
            try {
                Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
                Write-Host "Stopped PID $($p.ProcessId) ($($p.Name))" -ForegroundColor Green
            } catch {
                Write-Host "Failed to stop PID $($p.ProcessId): $_" -ForegroundColor Yellow
            }
        }
        Start-Sleep -Seconds 1
    } else {
        Write-Host "NoKill flag set: will not stop processes." -ForegroundColor Yellow
    }
} else {
    Write-Host "No running processes found that reference the venv." -ForegroundColor Green
}

# Remove existing venv
if (Test-Path $venvFull) {
    if ($Auto) {
        Write-Host "Auto mode: removing existing $venvRel..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force $venvFull
        Write-Host "$venvRel removed." -ForegroundColor Green
    } else {
        $confirm = Read-Host "Remove existing $venvRel and recreate it? This will delete the folder. (y/N)"
        if ($confirm -notmatch '^[yY]') {
            Write-Host "Aborting per user request." -ForegroundColor Yellow
            exit 0
        }
        Write-Host "Removing $venvRel..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force $venvFull
        Write-Host "$venvRel removed." -ForegroundColor Green
    }
} else {
    Write-Host "No existing $venvRel found, creating a new one." -ForegroundColor Green
}

# Determine python to use
if ($PythonPath -and (Test-Path $PythonPath)) {
    $pythonToUse = $PythonPath
} elseif (Test-Path 'C:\\Python313\\python.exe') {
    $pythonToUse = 'C:\\Python313\\python.exe'
} else {
    $pythonToUse = 'python'
}
Write-Host "Using python: $pythonToUse" -ForegroundColor Cyan

Write-Host "Creating venv..." -ForegroundColor Cyan
& $pythonToUse -m venv $venvFull --copies
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create venv (exit code $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}

$venvPy = (Resolve-Path (Join-Path $venvFull 'Scripts\\python.exe')).Path
Write-Host "Venv python: $venvPy" -ForegroundColor Green

# Upgrade pip tooling (use array splatting to avoid quoting/argument issues)
Write-Host "Upgrading pip, setuptools, wheel inside venv..." -ForegroundColor Cyan
$pipUpgradeArgs = @('-m','pip','install','-U','pip','setuptools','wheel')
& $venvPy @pipUpgradeArgs

# If LLVM clang exists, use short-path (Progra~1) to avoid spaces
$clangPath = 'C:\\Program Files\\LLVM\\bin\\clang.exe'
$clangShort = 'C:\\Progra~1\\LLVM\\bin\\clang.exe'
if (Test-Path $clangPath) {
    Write-Host "Found clang at $clangPath. Setting CC to $clangShort" -ForegroundColor Cyan
    $env:CC = $clangShort
} else {
    Write-Host "clang not found at $clangPath. Will not set CC." -ForegroundColor Yellow
}

# Attempt binary-only install first (use ArgumentList to avoid quoting issues)
$binaryPkgs = @('blis','thinc','spacy')
Write-Host "Attempting binary-only install for: $($binaryPkgs -join ', ')" -ForegroundColor Cyan
$binArgs = @('-m','pip','install','--only-binary',':all:') + $binaryPkgs
& $venvPy @binArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "Binary-only install failed or some wheels missing — trying fallback allowing source builds..." -ForegroundColor Yellow
    $fallbackArgs = @('-m','pip','install') + $binaryPkgs
    & $venvPy @fallbackArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Fallback install still failed. If this is 'blis' failing to build, consider installing Microsoft Build Tools or using conda/mamba." -ForegroundColor Red
        Write-Host "Conda suggestion: mamba create -n aimusic python=3.10 -c conda-forge blis thinc spacy audiocraft" -ForegroundColor Cyan
    } else {
        Write-Host "Fallback install succeeded." -ForegroundColor Green
    }
} else {
    Write-Host "Binary-only install succeeded for available packages." -ForegroundColor Green
}

# Attempt audiocraft install (may require extra steps)
Write-Host "Attempting to install audiocraft via pip (may not be available on PyPI)." -ForegroundColor Cyan
# Some build environments prefer clang via CC. For audiocraft older dependency pins this can force a clang compile
# that fails; temporarily unset CC so MSVC is used when available.
$savedCC = $env:CC
Try {
    if ($env:CC) { Remove-Item Env:CC -ErrorAction SilentlyContinue }
    $audiocraftArgs = @('-m','pip','install','audiocraft')
    & $venvPy @audiocraftArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pip could not find/install audiocraft in the venv. It may require conda or specific system deps. See project docs or use conda-forge." -ForegroundColor Yellow
    }
} Finally {
    if ($null -ne $savedCC) { $env:CC = $savedCC } else { Remove-Item Env:CC -ErrorAction SilentlyContinue }
}

if ($InstallAll) {
    if (-Not (Test-Path 'requirements.txt')) {
        Write-Host "requirements.txt not found in repo root. Skipping full install." -ForegroundColor Yellow
    } else {
        Write-Host "Installing full requirements.txt (this can take a long time)..." -ForegroundColor Cyan
        $reqArgs = @('-m','pip','install','-r','requirements.txt')
        & $venvPy @reqArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Host "One or more packages failed to install. Check the pip output above for details." -ForegroundColor Red
        }
    }
}

Write-Host "All done. To activate the venv run:" -ForegroundColor Cyan
Write-Host "    .\\.venv\\Scripts\\Activate.ps1" -ForegroundColor Green
Write-Host "Then run your usual setup or tests." -ForegroundColor Cyan

exit 0
