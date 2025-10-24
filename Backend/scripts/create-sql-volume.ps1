<#
.SYNOPSIS
    Create a persistent volume directory for SQL container data.

.DESCRIPTION
    This script creates a timestamped directory for SQL Server container volumes
    to store songs database data persistently. The volume directory is created
    in the user's home directory under .sqlcontainers.

.PARAMETER containerName
    The name of the SQL container (e.g., "songs-db", "music-db")

.EXAMPLE
    .\create-sql-volume.ps1 -containerName "songs-db"
    Creates: C:\Users\<username>\.sqlcontainers\songs-db_20251019123045

.NOTES
    Author: AiMusicSeparator-Backend Team
    Date: October 19, 2025
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$containerName
)

# Get user's home directory
$homeDir = [System.Environment]::GetFolderPath('UserProfile')
$volumeDirectory = "$homeDir\.sqlcontainers"

# Create base volume directory if it doesn't exist
if (-not (Test-Path -Path $volumeDirectory)) {
    Write-Host "Creating base volume directory: $volumeDirectory" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $volumeDirectory -Force | Out-Null
}

# Create timestamped volume name
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$volumeName = "${containerName}_$timestamp"
$containerDirectory = "$volumeDirectory\$volumeName"

# Create container-specific directory
if (-not (Test-Path -Path $containerDirectory)) {
    Write-Host "Creating container volume: $containerDirectory" -ForegroundColor Green
    New-Item -ItemType Directory -Path $containerDirectory -Force | Out-Null
}

# Create subdirectories for SQL Server data
$dataDir = "$containerDirectory\data"
$logDir = "$containerDirectory\log"
$backupDir = "$containerDirectory\backup"

foreach ($dir in @($dataDir, $logDir, $backupDir)) {
    if (-not (Test-Path -Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Output the path for use in docker-compose or scripts
Write-Output $containerDirectory

# Create a metadata file
$metadata = @{
    ContainerName = $containerName
    CreatedAt = (Get-Date).ToString("o")
    VolumePath = $containerDirectory
    Timestamp = $timestamp
} | ConvertTo-Json

$metadataFile = "$containerDirectory\metadata.json"
$metadata | Out-File -FilePath $metadataFile -Encoding UTF8

Write-Host "`nVolume created successfully!" -ForegroundColor Green
Write-Host "Container Name: $containerName" -ForegroundColor Yellow
Write-Host "Volume Path: $containerDirectory" -ForegroundColor Yellow
Write-Host "Data Directory: $dataDir" -ForegroundColor Yellow
Write-Host "Log Directory: $logDir" -ForegroundColor Yellow
Write-Host "Backup Directory: $backupDir" -ForegroundColor Yellow

# Return the path for scripting
return $containerDirectory
