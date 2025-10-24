<#
Install NVIDIA CUDA-specific Python packages (CUDA 12 variants) into a venv or conda env.

Usage examples:
  # Install into repo venv (default assumption)
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_nvidia_cuda_libs.ps1

  # Install into a conda env named 'aimusic'
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_nvidia_cuda_libs.ps1 -CondaEnv aimusic

Parameters:
  -PythonExe   : explicit path to Python executable to use (overrides venv detection)
  -CondaEnv    : name of conda env to use (uses `conda run -n <env> python -m pip`)
  -RetryCount  : number of retries per package (default 2)
  -ExtraIndex  : extra pip index URL for NVIDIA packages (default https://pypi.ngc.nvidia.com)

This script will attempt to pip-install the following packages (CUDA 12 builds):
  nvidia-cufft-cu12
  nvidia-curand-cu12
  nvidia-cusolver-cu12
  nvidia-cusparse-cu12
  nvidia-npp-cu12
  nvidia-nvfatbin-cu12
  nvidia-nvjitlink-cu12
  nvidia-nvjpeg-cu12
  nvidia-nvml-dev-cu12
  nvidia-nvtx-cu12

It prefers to install from NVIDIA's index via --extra-index-url. If a package fails, it will retry.
#>

param(
    [string]$PythonExe = '.\\.venv\\Scripts\\python.exe',
    [string]$CondaEnv = '',
    [int]$RetryCount = 2,
    [string]$ExtraIndex = 'https://pypi.ngc.nvidia.com'
)

Set-StrictMode -Version Latest

function Resolve-PythonExe {
    param($candidate)
    if ($candidate -and (Test-Path $candidate)) { return (Get-Item $candidate).FullName }
    # common venv location
    $venvPython = Join-Path -Path (Get-Location) -ChildPath '.venv\\Scripts\\python.exe'
    if (Test-Path $venvPython) { return (Get-Item $venvPython).FullName }
    # fallback to system python in PATH
    $p = Get-Command python -ErrorAction SilentlyContinue
    if ($p) { return $p.Source }
    throw "No python executable found. Provide -PythonExe path or create a venv at .\.venv"
}

$packages = @(
    'nvidia-cufft-cu12',
    'nvidia-curand-cu12',
    'nvidia-cusolver-cu12',
    'nvidia-cusparse-cu12',
    'nvidia-npp-cu12',
    'nvidia-nvfatbin-cu12',
    'nvidia-nvjitlink-cu12',
    'nvidia-nvjpeg-cu12',
    'nvidia-nvml-dev-cu12',
    'nvidia-nvtx-cu12'
)

try {
    $python = Resolve-PythonExe -candidate $PythonExe
} catch {
    Write-Error $_.Exception.Message
    exit 3
}

Write-Host "Using Python: $python"
Write-Host "Using extra pip index: $ExtraIndex"

function Run-PipInstall {
    param([string]$pkg)
    $cmdBase = @($python, '-m', 'pip', 'install', '--prefer-binary', '--no-cache-dir', '--extra-index-url', $ExtraIndex, $pkg)
    $attempt = 0
    while ($attempt -le $RetryCount) {
        $attempt++
        Write-Host "Installing $pkg (attempt $attempt of $($RetryCount+1))..."
        if ($CondaEnv) {
            # Use conda run to avoid requiring activation
            $runCmd = @('conda','run','-n',$CondaEnv) + $cmdBase
            $process = Start-Process -FilePath $runCmd[0] -ArgumentList $runCmd[1..($runCmd.Length-1)] -NoNewWindow -Wait -PassThru -RedirectStandardOutput "stdout.txt" -RedirectStandardError "stderr.txt"
        } else {
            $process = Start-Process -FilePath $cmdBase[0] -ArgumentList $cmdBase[1..($cmdBase.Length-1)] -NoNewWindow -Wait -PassThru -RedirectStandardOutput "stdout.txt" -RedirectStandardError "stderr.txt"
        }
        $rc = $process.ExitCode
        $out = Get-Content -Raw -ErrorAction SilentlyContinue stdout.txt
        $err = Get-Content -Raw -ErrorAction SilentlyContinue stderr.txt
        if ($rc -eq 0) {
            Write-Host "OK: $pkg"
            Remove-Item stdout.txt, stderr.txt -ErrorAction SilentlyContinue
            return $true
        } else {
            Write-Warning "Failed installing $pkg (exit $rc)."
            if ($out) { Write-Host "STDOUT:`n$out" }
            if ($err) { Write-Host "STDERR:`n$err" }
            if ($attempt -gt $RetryCount) {
                Write-Error "Giving up on $pkg after $attempt attempts."
                Remove-Item stdout.txt, stderr.txt -ErrorAction SilentlyContinue
                return $false
            }
            Start-Sleep -Seconds (5 * $attempt)
        }
    }
}

$allOk = $true
foreach ($p in $packages) {
    $ok = Run-PipInstall -pkg $p
    if (-not $ok) { $allOk = $false }
}

if ($allOk) { Write-Host "All NVIDIA CUDA packages installed successfully." -ForegroundColor Green; exit 0 }
else { Write-Error "Some NVIDIA CUDA packages failed to install. Check output above for details."; exit 4 }
