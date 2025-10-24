<#
enable-pwsh-allow.ps1

Safe helper to set PowerShell execution policy for the CurrentUser and
unblock PowerShell script files in a repository or path. This script is
intended to be run locally by a developer who understands the security
implications.

Usage:
  # Interactive (prompts for confirmation)
  pwsh -NoProfile -File scripts/enable-pwsh-allow.ps1

  # Non-interactive (force, set repo root explicitly)
  pwsh -NoProfile -File scripts/enable-pwsh-allow.ps1 -Path . -Force

This will:
  - Set ExecutionPolicy for CurrentUser to Bypass (non-admin)
  - Recursively Unblock-File for common PowerShell script extensions

Warning: Changing execution policy and unblocking files can increase risk
if malicious scripts are present. Inspect files before running.
#>

param(
    [string]
    $Path = ".",

    [switch]
    $Force
)

function Confirm-Or-Exit($message) {
    if ($Force) { return }
    Write-Host "" -ForegroundColor Yellow
    Write-Host "$message" -ForegroundColor Yellow
    $resp = Read-Host "Proceed? (Y/N)"
    if ($resp -notin @('Y','y','Yes','yes')) {
        Write-Host "Aborting by user request." -ForegroundColor Red
        exit 2
    }
}

try {
    $fullPath = Resolve-Path -LiteralPath $Path
} catch {
    Write-Error "Path not found: $Path"
    exit 1
}

Write-Host "PowerShell allow helper" -ForegroundColor Cyan
Write-Host "Target path: $fullPath"

Confirm-Or-Exit "This will set ExecutionPolicy (CurrentUser) to Bypass and unblock files under the path above."

try {
    # Set execution policy for current user to Bypass; this does not require admin
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass -Force
    Write-Host "Set ExecutionPolicy CurrentUser -> Bypass" -ForegroundColor Green
} catch {
    Write-Warning "Failed to set ExecutionPolicy: $_"
}

# Unblock common PowerShell files recursively
$exts = @('*.ps1','*.psm1','*.psd1','*.ps1xml')
foreach ($ext in $exts) {
    Write-Host "Unblocking $ext files under $fullPath" -ForegroundColor Cyan
    Get-ChildItem -Path $fullPath -Recurse -Include $ext -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            try {
                Unblock-File -Path $_.FullName -ErrorAction Stop
                Write-Host "Unblocked: $($_.FullName)" -ForegroundColor Green
            } catch {
                Write-Warning "Failed to unblock $($_.FullName): $_"
            }
        }
}

Write-Host "Done. Review changes and exercise caution when running scripts." -ForegroundColor Cyan
