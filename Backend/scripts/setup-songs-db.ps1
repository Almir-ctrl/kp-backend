<#
.SYNOPSIS
    Complete setup for songs database.

.DESCRIPTION
    Starts SQL Server container, creates database, and initializes schema.

.EXAMPLE
    .\setup-songs-db.ps1
    Complete setup with default settings
#>

param (
    [string]$ContainerName = "SongsDB",
    [string]$SqlPassword = $env:lQyTXhwzmAzRLBNv7
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Songs Database Setup for AiMusicSeparator         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Step 1: Start SQL Server container
Write-Host "Step 1: Starting SQL Server container..." -ForegroundColor Green
$startScript = Join-Path $scriptDir "start-songs-db.ps1"

if (-not (Test-Path $startScript)) {
    Write-Error "Start script not found: $startScript"
    exit 1
}

& $startScript -ContainerName $ContainerName -SqlPassword $SqlPassword

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start SQL Server container"
    exit 1
}

# Read connection details from .env file
$backendDir = Split-Path -Parent $scriptDir
$envFile = Join-Path $backendDir ".env.songs-db"

if (-not (Test-Path $envFile)) {
    Write-Error "Connection details not found: $envFile"
    exit 1
}

$envContent = Get-Content $envFile -Raw
$port = if ($envContent -match 'SONGS_DB_PORT=(\d+)') { $matches[1] } else { "1433" }
$password = if ($envContent -match 'SONGS_DB_PASSWORD=(.+)') { $matches[1] } else { $SqlPassword }

# Step 2: Wait for SQL Server to be fully ready
Write-Host "`nStep 2: Waiting for SQL Server to be fully ready..." -ForegroundColor Green
Start-Sleep -Seconds 15

# Step 3: Initialize database schema
Write-Host "`nStep 3: Initializing database schema..." -ForegroundColor Green
$initScript = Join-Path $scriptDir "init-songs-db.sql"

if (-not (Test-Path $initScript)) {
    Write-Error "Initialization script not found: $initScript"
    exit 1
}

# Copy init script to container
Write-Host "Copying initialization script to container..." -ForegroundColor Cyan
docker cp $initScript "${ContainerName}:/tmp/init-songs-db.sql"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to copy initialization script"
    exit 1
}

# Execute initialization script
Write-Host "Executing initialization script..." -ForegroundColor Cyan
docker exec $ContainerName /opt/mssql-tools18/bin/sqlcmd `
    -S localhost -U SA -P "$password" -C `
    -i /tmp/init-songs-db.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Database schema initialized successfully!" -ForegroundColor Green
} else {
    Write-Error "Failed to initialize database schema"
    exit 1
}

# Step 4: Verify setup
Write-Host "`nStep 4: Verifying setup..." -ForegroundColor Green
$verifyQuery = @"
SELECT 
    'Tables' AS Category,
    COUNT(*) AS Count
FROM SongsDB.INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
UNION ALL
SELECT 
    'Views' AS Category,
    COUNT(*) AS Count
FROM SongsDB.INFORMATION_SCHEMA.VIEWS
UNION ALL
SELECT 
    'Procedures' AS Category,
    COUNT(*) AS Count
FROM SongsDB.INFORMATION_SCHEMA.ROUTINES
WHERE ROUTINE_TYPE = 'PROCEDURE';
"@

docker exec $ContainerName /opt/mssql-tools18/bin/sqlcmd `
    -S localhost -U SA -P "$password" -C `
    -Q "$verifyQuery"

# Create Python database connector module
Write-Host "`nStep 5: Creating Python database connector..." -ForegroundColor Green
$serverDir = Join-Path $backendDir "server"
$dbModulePath = Join-Path $serverDir "songs_db.py"

$pythonModule = @"
"""Songs Database connector for AiMusicSeparator-Backend.

This module provides database access for storing and retrieving songs,
processing jobs, transcriptions, and analysis results.
"""

import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

try:
    import pyodbc
except ImportError:
    pyodbc = None
    print("Warning: pyodbc not installed. Install with: pip install pyodbc")


class SongsDatabase:
    """Database connector for Songs database."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize database connection.
        
        Args:
            connection_string: SQL Server connection string.
                If not provided, reads from environment variables.
        """
        if pyodbc is None:
            raise ImportError("pyodbc is required. Install with: pip install pyodbc")
        
        self.connection_string = connection_string or self._get_connection_string()
    
    def _get_connection_string(self) -> str:
        """Get connection string from environment variables."""
        host = os.getenv('SONGS_DB_HOST', 'localhost')
        port = os.getenv('SONGS_DB_PORT', '4521')
        user = os.getenv('SONGS_DB_USER', 'agysha')
        password = os.getenv('SONGS_DB_PASSWORD')
        database = os.getenv('SONGS_DB_NAME', 'SongsDB')
        
        if not password:
            raise ValueError("SONGS_DB_PASSWORD environment variable not set")
        
        driver = '{ODBC Driver 18 for SQL Server}'
        return (
            f'DRIVER={driver};'
            f'SERVER={host},{port};'
            f'DATABASE={database};'
            f'UID={user};'
            f'PWD={password};'
            f'TrustServerCertificate=yes;'
        )
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = pyodbc.connect(self.connection_string)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_song(self, file_id: str, filename: str, **kwargs) -> str:
        """Create a new song record.
        
        Args:
            file_id: Unique file identifier
            filename: Stored filename
            **kwargs: Additional fields (title, artist, file_size, etc.)
        
        Returns:
            Song ID (UUID)
        """
        song_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Songs (
                    Id, FileId, FileName, Title, Artist, Album,
                    OriginalFileName, FileSize, Duration, FileExtension,
                    MimeType, Status, Metadata, CreatedBy
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                song_id,
                file_id,
                filename,
                kwargs.get('title'),
                kwargs.get('artist'),
                kwargs.get('album'),
                kwargs.get('original_filename'),
                kwargs.get('file_size'),
                kwargs.get('duration'),
                kwargs.get('file_extension'),
                kwargs.get('mime_type'),
                kwargs.get('status', 'uploaded'),
                json.dumps(kwargs.get('metadata', {})),
                kwargs.get('created_by')
            ))
        
        return song_id
    
    def create_job(
        self,
        song_id: str,
        model_name: str,
        job_type: str,
        request_id: Optional[str] = None
    ) -> str:
        """Create a processing job record.
        
        Args:
            song_id: Song ID
            model_name: Model to use for processing
            job_type: Type of job (separation, transcription, etc.)
            request_id: X-Request-ID for tracing
        
        Returns:
            Job ID (UUID)
        """
        job_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ProcessingJobs (
                    Id, JobId, SongId, ModelName, JobType,
                    Status, RequestId, StartedAt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_id,
                song_id,
                model_name,
                job_type,
                'processing',
                request_id,
                datetime.utcnow()
            ))
        
        return job_id
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float = None,
        message: str = None,
        error: str = None
    ):
        """Update job status and progress.
        
        Args:
            job_id: Job ID
            status: New status (pending, processing, completed, failed)
            progress: Progress percentage (0-100)
            message: Status message
            error: Error message if failed
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status == 'completed':
                cursor.execute("""
                    UPDATE ProcessingJobs
                    SET Status = ?, Progress = ?, Message = ?,
                        CompletedAt = ?, LastModified = ?
                    WHERE JobId = ?
                """, (status, progress or 100, message, datetime.utcnow(), datetime.utcnow(), job_id))
            elif status == 'failed':
                cursor.execute("""
                    UPDATE ProcessingJobs
                    SET Status = ?, Message = ?, ErrorMessage = ?,
                        CompletedAt = ?, LastModified = ?
                    WHERE JobId = ?
                """, (status, message, error, datetime.utcnow(), datetime.utcnow(), job_id))
            else:
                cursor.execute("""
                    UPDATE ProcessingJobs
                    SET Status = ?, Progress = ?, Message = ?, LastModified = ?
                    WHERE JobId = ?
                """, (status, progress, message, datetime.utcnow(), job_id))
    
    def get_song(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get song by file ID.
        
        Args:
            file_id: File identifier
        
        Returns:
            Song record as dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM Songs WHERE FileId = ?
            """, (file_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
    
    def log_audit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        request_id: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log an audit entry.
        
        Args:
            entity_type: Type of entity (song, job, track, etc.)
            entity_id: Entity identifier
            action: Action performed
            request_id: X-Request-ID for tracing
            details: Additional details as dictionary
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO AuditLog (
                    RequestId, EntityType, EntityId, Action, Details
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                request_id,
                entity_type,
                entity_id,
                action,
                json.dumps(details or {})
            ))


# Example usage
if __name__ == '__main__':
    # Test connection
    try:
        db = SongsDatabase()
        print("✅ Database connection successful!")
        
        # Test query
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            print(f"SQL Server Version: {version[:50]}...")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
"@

$pythonModule | Out-File -FilePath $dbModulePath -Encoding UTF8
Write-Host "Python module created: $dbModulePath" -ForegroundColor Green

# Display final summary
Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            Setup Complete Successfully!             ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "📦 Docker Volume: " -ForegroundColor Yellow
Write-Host "   - ${containerName}-backup (for database backups)" -ForegroundColor White
Write-Host "   Note: Data stored in container (survives restarts, not removals)" -ForegroundColor Gray

Write-Host "🔌 Connection: localhost:$port" -ForegroundColor Yellow
Write-Host "🔑 Password saved in: $envFile" -ForegroundColor Yellow
Write-Host "🐍 Python module: $dbModulePath" -ForegroundColor Yellow

Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Install Python SQL driver: pip install pyodbc" -ForegroundColor White
Write-Host "2. Load environment: . $envFile (PowerShell)" -ForegroundColor White
Write-Host "3. Test Python connection: python $dbModulePath" -ForegroundColor White
Write-Host "4. Use in your Flask app: from server.songs_db import SongsDatabase" -ForegroundColor White

Write-Host "`n✅ Database is ready for use!" -ForegroundColor Green
