# PowerShell helper to run the CI-safe smoke tests locally
# Usage: .\scripts\run_smoke_test.ps1
# - Starts the backend (in the foreground)
# - Runs pytest -m ci_smoke and writes junit xml
# - Runs scripts/smoke_test.py
# - Stops the backend

param(
    [string]$Python = 'python',
    [int]$Port = 5000
)

$env:CI_SMOKE = 'true'

Write-Host "Starting backend with CI_SMOKE=$env:CI_SMOKE..."
# Start backend in background and capture its PID
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $Python
$startInfo.Arguments = 'app.py'
$startInfo.WorkingDirectory = (Get-Location).Path
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$startInfo.UseShellExecute = $false
$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $startInfo
$null = $proc.Start()
Start-Sleep -Seconds 2
Write-Host "Backend started (PID=$($proc.Id)). Waiting for startup..."

# Wait for /health to be available (timeout 15s)
$healthOk = $false
$maxWait = 15
for ($i=0; $i -lt $maxWait; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $healthOk = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if (-not $healthOk) {
    Write-Host "Backend did not respond at /health within $maxWait seconds. Continuing anyway..." -ForegroundColor Yellow
}

# Run pytest for ci_smoke marker
Write-Host "Running pytest -m ci_smoke..."
$pytestArgs = "-m ci_smoke --junitxml=pytest_ci_smoke.xml"
$exitCode = & $Python -m pytest $pytestArgs
Write-Host "pytest finished with exit code $exitCode"

# Run smoke script
Write-Host "Running scripts/smoke_test.py..."
& $Python scripts/smoke_test.py

# Stop backend
try {
    if ($proc -and -not $proc.HasExited) {
        Write-Host "Stopping backend (PID=$($proc.Id))..."
        $proc.Kill()
        $proc.WaitForExit(5000)
    }
} catch {
    Write-Host "Failed to stop backend process: $_" -ForegroundColor Red
}

exit $exitCode
