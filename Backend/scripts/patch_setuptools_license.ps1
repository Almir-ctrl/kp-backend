<#
Patch a setuptools dist.py file inside a pip build-overlay temp path to adjust the license string.

This script will:
  - back up the target file to <target>.bak
  - try to replace an existing `license = "..."` assignment
  - if not found, insert `license = "MIT AND (Apache-2.0 OR BSD-2-Clause)"` before the
    `class Distribution` definition (a reasonable fallback location)

Usage:
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\patch_setuptools_license.ps1 -TargetFile "C:\...\pip-build-env-*/overlay/Lib/site-packages/setuptools/dist.py"

Note: This edits a transient pip build-overlay file. A better long-term fix is to pin
      setuptools/pip or use conda for binary packages. Use this script only for local
      troubleshooting and re-run for new pip build overlays.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$TargetFile
)

if (-not (Test-Path -Path $TargetFile)) {
    Write-Error "Target file not found: $TargetFile"
    exit 2
}

$bak = "${TargetFile}.bak"
try {
    Copy-Item -Path $TargetFile -Destination $bak -Force -ErrorAction Stop
    Write-Host "Backup written to: $bak"
} catch {
    Write-Error "Failed to create backup: $_"
    exit 3
}

try {
    $content = Get-Content -Raw -Path $TargetFile -ErrorAction Stop
} catch {
    Write-Error "Failed to read target file: $_"
    exit 4
}

# Replacement value we want to ensure exists in the file
$replacementLine = 'license = "MIT AND (Apache-2.0 OR BSD-2-Clause)"'

# Use a here-string for the pattern to avoid nested-quote pain. This pattern matches:
#   license = "..."  OR  license = '...'
$pattern = @'
license\s*=\s*(['"]).*?\1
'@

try {
    if ([regex]::IsMatch($content, $pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)) {
        $new = [regex]::Replace($content, $pattern, $replacementLine, [System.Text.RegularExpressions.RegexOptions]::Singleline)
        Set-Content -Path $TargetFile -Value $new -Force
        Write-Host "Rewrote existing license assignment in $TargetFile"
        exit 0
    }
} catch {
    Write-Warning "Regex replace attempt failed: $_"
}

# If we reach here, no existing license assignment was found; insert the replacement
# before the class Distribution definition (if present), otherwise at top-of-file.
try {
    $lines = Get-Content -Path $TargetFile -ErrorAction Stop
} catch {
    Write-Error "Failed to read target file lines: $_"
    exit 5
}

$insertAt = -1
for ($i = 0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match '^class\s+Distribution') { $insertAt = [math]::Max(0, $i - 1); break }
}

if ($insertAt -ge 0) {
    $out = @()
    if ($insertAt -ge 0) { $out += $lines[0..$insertAt] }
    $out += $replacementLine
    if ($insertAt + 1 -lt $lines.Length) { $out += $lines[($insertAt + 1)..($lines.Length - 1)] }
    try {
        $out | Set-Content -Path $TargetFile -Force
        Write-Host "Inserted license assignment before class Distribution (line $($insertAt + 1))"
        exit 0
    } catch {
        Write-Error "Failed to write modified content: $_"
        exit 6
    }
} else {
    # No Distribution class found — prepend the assignment at the top
    try {
        $final = @($replacementLine) + $lines
        $final | Set-Content -Path $TargetFile -Force
        Write-Host "Prepended license assignment at top of file"
        exit 0
    } catch {
        Write-Error "Failed to prepend license assignment: $_"
        exit 7
    }
}
<#
Patch a setuptools dist.py file inside a pip build-overlay temp path to adjust the license string.
This is intended for developer troubleshooting when pip build isolates provide setuptools with restrictive metadata.
<#
Patch a setuptools dist.py file inside a pip build-overlay temp path to adjust the license string.
This is intended for developer troubleshooting when pip build isolates provide setuptools with restrictive metadata.

Usage:
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\patch_setuptools_license.ps1 -TargetFile "C:\Users\<you>\AppData\Local\Temp\pip-build-env-*/overlay/Lib/site-packages/setuptools/dist.py"

The script will create a backup copy next to the target file (.bak) before modifying.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetFile
)

if (-not (Test-Path $TargetFile)) {
    Write-Error "Target file not found: $TargetFile"
    exit 2
}

$bak = "$TargetFile.bak"
Copy-Item -Path $TargetFile -Destination $bak -Force
Write-Host "Backup written to $bak"

try {
    $content = Get-Content -Raw -Path $TargetFile -ErrorAction Stop
} catch {
    Write-Error "Failed to read target file: $_"
    exit 3
}

# Pattern matches license = "..." or license = '...'
# Use single-quoted string and double up single quotes inside the quoted string to include a single quote
$pattern = 'license\s*=\s*[''"].*?[''" ]'
$replacement = 'license = "MIT AND (Apache-2.0 OR BSD-2-Clause)"'

if ($content -match $pattern) {
    $new = [regex]::Replace($content, $pattern, $replacement)
    Set-Content -Path $TargetFile -Value $new -Force
    Write-Host "Rewrote license field in $TargetFile"
    exit 0
}

# If not found, insert a license assignment near the top (before the Distribution class) as a fallback
$lines = Get-Content -Path $TargetFile
$insertAt = 0
for ($i=0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match '^class\s+Distribution') { $insertAt = [math]::Max(0, $i-1); break }
}

$out = @()
if ($insertAt -ge 0) { $out += $lines[0..$insertAt] }
$out += $replacement
if ($insertAt+1 -lt $lines.Length) { $out += $lines[($insertAt+1)..($lines.Length-1)] }
$out | Set-Content -Path $TargetFile -Force
Write-Host "Inserted license assignment at line $($insertAt+1)"
exit 0
    # Try replacing direct 'license = "..."' assignment
    $pattern = 'license\s*=\s*[''"].*?[''" ]'
    if ($content -match $pattern) {
        $content = [regex]::Replace($content, $pattern, 'license = "MIT AND (Apache-2.0 OR BSD-2-Clause)"')
        Set-Content -Path $TargetFile -Value $content -Force
        Write-Host "Rewrote license field in $TargetFile"
        exit 0
    } else {
        Write-Host "No direct license assignment found in file. Searching for classifier patterns..."
    }

    # Attempt to inject license variable near top if not present
    if ($content -notmatch 'license\s*=') {
        $lines = Get-Content -Path $TargetFile
        $insertAt = 0
        for ($i=0; $i -lt $lines.Length; $i++) {
            if ($lines[$i] -match '^class\s+Distribution') { $insertAt = [math]::Max(0, $i-1); break }
        }
        $out = @()
        if ($insertAt -ge 0) { $out += $lines[0..$insertAt] }
        $out += 'license = "MIT AND (Apache-2.0 OR BSD-2-Clause)"'
        if ($insertAt+1 -lt $lines.Length) { $out += $lines[($insertAt+1)..($lines.Length-1)] }
        $out | Set-Content -Path $TargetFile -Force
        Write-Host "Inserted license assignment at line $($insertAt+1)"
        exit 0
    }

    Write-Host "No modifications applied. File may use a different pattern than expected." -ForegroundColor Yellow
    exit 3
