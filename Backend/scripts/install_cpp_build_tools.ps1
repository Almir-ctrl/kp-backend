<#
.SYNOPSIS
  Helper script to install C/C++ build toolchains on Windows.

.DESCRIPTION
  Provides options to (1) download and install Visual Studio Build Tools with the
  C++ workload, (2) install LLVM/Clang via winget/choco, or (3) both.

  The script defaults to a dry-run mode and will only show the steps it would take.
  Use -Method and -AutoConfirm to run unattended installations (requires admin).

.EXAMPLES
  # Dry run (default)
  .\scripts\install_cpp_build_tools.ps1

  # Install Visual Studio Build Tools (C++ workload)
  .\scripts\install_cpp_build_tools.ps1 -Method vsbuildtools -AutoConfirm

  # Install LLVM via winget (if available)
  .\scripts\install_cpp_build_tools.ps1 -Method llvm -AutoConfirm

NOTES
  - Running installers requires Administrator privileges. The script will warn
    if it is not elevated.
  - Be prepared for large downloads (several hundreds MB).
#>

param(
    [ValidateSet('vsbuildtools','llvm','both','dryrun')]
    [string]$Method = 'dryrun',
    [switch]$AutoConfirm
)

function Test-IsAdmin {
    $current = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($current)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-DryRun($Text) {
    Write-Host "[DRY-RUN] $Text" -ForegroundColor Yellow
}

function Download-File($Url, $OutPath) {
    Write-Host "Downloading $Url -> $OutPath"
    Invoke-WebRequest -Uri $Url -OutFile $OutPath -UseBasicParsing
    return $OutPath
}

function Install-VSBuildTools {
    param([switch]$Run)
    $vsUrl = 'https://aka.ms/vs/17/release/vs_BuildTools.exe'
    $out = Join-Path $env:TEMP 'vs_BuildTools.exe'
    if ($Run) {
        Write-Host "Downloading Visual Studio Build Tools from $vsUrl"
        Download-File -Url $vsUrl -OutPath $out

        $workloads = @(
            'Microsoft.VisualStudio.Workload.VCTools' # C++ build tools
        )
        $components = @(
            'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
            'Microsoft.VisualStudio.Component.Windows10SDK.19041' # Windows 10 SDK (example)
        )

        $add = ($workloads + $components) -join ' '
        $args = "--quiet --wait --norestart --nocache --add $add --includeRecommended"

        Write-Host "Running installer (this can take a while): $out $args"
        & $out $args
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Visual Studio Build Tools installed successfully." -ForegroundColor Green
        } else {
            Write-Host "Installer exited with code $LASTEXITCODE" -ForegroundColor Red
        }
    } else {
        Invoke-DryRun "Would download $vsUrl and run with C++ workload and Windows SDK"
    }
}

function Install-LLVM {
    param([switch]$Run)
    # Prefer winget if available, fall back to chocolatey if winget not present
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    if ($Run) {
        if ($winget) {
            Write-Host "Installing LLVM via winget"
            winget install --id LLVM.LLVM -e --accept-package-agreements --accept-source-agreements
        } elseif ($choco) {
            Write-Host "Installing LLVM via chocolatey"
            choco install llvm -y
        } else {
            Write-Host "Neither winget nor choco detected. Please install one of them or install LLVM manually." -ForegroundColor Yellow
        }
    } else {
        if ($winget) {
            Invoke-DryRun "Would run: winget install --id LLVM.LLVM -e --accept-package-agreements --accept-source-agreements"
        } elseif ($choco) {
            Invoke-DryRun "Would run: choco install llvm -y"
        } else {
            Invoke-DryRun "Would prompt user to install winget or chocolatey and then install LLVM"
        }
    }
}

function Set-CC-ShortPath {
    param([string]$Preferred = 'clang')
    # Try to find clang.exe or cl.exe and suggest short-path form
    $clang = Get-Command clang -ErrorAction SilentlyContinue
    $cl = Get-Command cl -ErrorAction SilentlyContinue
    if ($clang) {
        $path = $clang.Path
    } elseif ($cl) {
        $path = $cl.Path
    } else {
        Write-Host "No clang or cl detected in PATH. Install a toolchain first." -ForegroundColor Yellow
        return
    }

    # Create short-path (8.3) if possible for parent folder
    $parent = Split-Path $path -Parent
    try {
        $short = (Get-Item $parent).PSPath
    } catch {
        $short = $parent
    }
    Write-Host "Detected compiler: $path"
    Write-Host "If you run into spaces-in-path issues, set CC to the short 8.3 path (example):"
    Write-Host "  `"$($short.Replace('\\','\\\\'))\\clang.exe`""
}

# Main logic
Write-Host "install_cpp_build_tools.ps1 - Method: $Method; AutoConfirm: $AutoConfirm"

if (-not (Test-IsAdmin)) {
    Write-Host "WARNING: This script is not running as Administrator. Installers will likely fail without elevation." -ForegroundColor Yellow
    Write-Host "Run PowerShell as Administrator and re-run the script for automatic installation."
}

switch ($Method) {
    'dryrun' {
        Install-VSBuildTools -Run:$false
        Install-LLVM -Run:$false
        break
    }
    'vsbuildtools' {
        if ($AutoConfirm) { Install-VSBuildTools -Run:$true } else { Install-VSBuildTools -Run:$false }
        break
    }
    'llvm' {
        if ($AutoConfirm) { Install-LLVM -Run:$true } else { Install-LLVM -Run:$false }
        break
    }
    'both' {
        if ($AutoConfirm) { Install-VSBuildTools -Run:$true; Install-LLVM -Run:$true } else { Install-VSBuildTools -Run:$false; Install-LLVM -Run:$false }
        break
    }
}

Write-Host "Done. If you installed tools, open a new elevated developer prompt or restart your shell." -ForegroundColor Cyan
