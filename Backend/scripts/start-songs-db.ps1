<#
.SYNOPSIS
    Start SQL Server container for songs database.

.DESCRIPTION
    Creates a persistent volume and starts a SQL Server container for storing
    songs metadata, transcriptions, and processing results.

.PARAMETER ContainerName
    Name for the SQL container (default: "songs-db")

.PARAMETER SqlPassword
    SA password for SQL Server (default: reads from env or generates secure)

.PARAMETER Port
    Port to expose SQL Server on (default: 1433)

.EXAMPLE
    .\start-songs-db.ps1
    Starts container with default settings

.EXAMPLE
    .\start-songs-db.ps1 -ContainerName "music-db" -Port 1434
    Starts container with custom name and port
#>

param (
    [string]$ContainerName = "songs-db",
    [string]$SqlPassword = $env:6URTGG3HGeoKG1g0,
    [int]$Port = 9375
)

# Generate secure password if not provided
if ([string]::IsNullOrEmpty($SqlPassword)) {
    $SqlPassword = -join ((65..90) + (97..122) + (48..57) + (33,35,36,37,38,42,43,45) | Get-Random -Count 16 | ForEach-Object {[char]$_})
    Write-Host "Generated SA Password: $SqlPassword" -ForegroundColor Yellow
    Write-Host "Save this password securely!" -ForegroundColor Red
}

# Validate password complexity
if ($SqlPassword.Length -lt 8) {
    Write-Error "Password must be at least 8 characters long"
    exit 1
}

Write-Host "`n=== Starting SQL Server Container for Songs Database ===" -ForegroundColor Cyan

# Create Docker named volume for backups only
Write-Host "`nCreating Docker volume for backups..." -ForegroundColor Cyan
docker volume create "${ContainerName}-backup" | Out-Null

Write-Host "Volume created: ${ContainerName}-backup" -ForegroundColor Gray
Write-Host "Note: Data and logs use container storage for compatibility" -ForegroundColor Gray

# Check if container already exists
$existingContainer = docker ps -a --filter "name=$ContainerName" --format "{{.Names}}"

if ($existingContainer -eq $ContainerName) {
    Write-Host "`nContainer '$ContainerName' already exists." -ForegroundColor Yellow
    $running = docker ps --filter "name=$ContainerName" --format "{{.Names}}"
    
    if ($running -eq $ContainerName) {
        Write-Host "Container is already running." -ForegroundColor Green
    } else {
        Write-Host "Starting existing container..." -ForegroundColor Cyan
        docker start $ContainerName
    }
} else {
    # Start new SQL Server container with backup volume only
    Write-Host "`nStarting SQL Server container..." -ForegroundColor Cyan
    
    docker run -d `
        --name $ContainerName `
        -e "ACCEPT_EULA=Y" `
        -e "SA_PASSWORD=$SqlPassword" `
        -e "MSSQL_PID=Developer" `
        -p "${Port}:1433" `
        -v "${ContainerName}-backup:/var/opt/mssql/backup" `
        --restart unless-stopped `
        mcr.microsoft.com/mssql/server:2022-latest

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nContainer started successfully!" -ForegroundColor Green
    } else {
        Write-Error "Failed to start container"
        exit 1
    }
}

# Wait for SQL Server to be ready
Write-Host "`nWaiting for SQL Server to be ready (this may take 30-60 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# Test connection with retries
Write-Host "Testing connection..." -ForegroundColor Cyan
$maxRetries = 6
$retryCount = 0
$connected = $false

while ($retryCount -lt $maxRetries -and -not $connected) {
    $connectionTest = docker exec $ContainerName /opt/mssql-tools18/bin/sqlcmd `
        -S localhost -U SA -P "$SqlPassword" -C `
        -Q "SELECT @@VERSION" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ SQL Server is ready!" -ForegroundColor Green
        $connected = $true
    } else {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "  Attempt $retryCount/$maxRetries - waiting..." -ForegroundColor Gray
            Start-Sleep -Seconds 10
        }
    }
}

if (-not $connected) {
    Write-Warning "Connection test failed after $maxRetries attempts. SQL Server may still be starting..."
    Write-Host "You can check logs with: docker logs $ContainerName" -ForegroundColor Yellow
}

# Display connection information
Write-Host "`n=== Connection Information ===" -ForegroundColor Cyan
Write-Host "Server: localhost,$Port" -ForegroundColor Yellow
Write-Host "User: agysha" -ForegroundColor Yellow
Write-Host "Password: $SqlPassword" -ForegroundColor Yellow

# Save connection string to .env file
$backendDir = Split-Path -Parent $scriptDir
$envFile = Join-Path $backendDir ".env.songs-db"

$connectionString = "Server=localhost,$Port;Database=SongsDB;User Id=SA;Password=$SqlPassword;TrustServerCertificate=True;"

@"
# Songs Database Connection
SONGS_DB_HOST=localhost
SONGS_DB_PORT=$Port
SONGS_DB_USER=SA
SONGS_DB_PASSWORD=$SqlPassword
SONGS_DB_NAME=SongsDB
SONGS_DB_CONNECTION_STRING=$connectionString
VOLUME_PATH=$volumePath
"@ | Out-File -FilePath $envFile -Encoding UTF8

Write-Host "`nConnection details saved to: $envFile" -ForegroundColor Green

# Display management commands
Write-Host "`n=== Management Commands ===" -ForegroundColor Cyan
Write-Host "Stop container:    docker stop $ContainerName" -ForegroundColor Yellow
Write-Host "Start container:   docker start $ContainerName" -ForegroundColor Yellow
Write-Host "Remove container:  docker rm -f $ContainerName" -ForegroundColor Yellow
Write-Host "View logs:         docker logs $ContainerName" -ForegroundColor Yellow
Write-Host "Connect:           docker exec -it $ContainerName /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P '$SqlPassword' -C" -ForegroundColor Yellow

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
