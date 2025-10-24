# Songs Database Scripts

PowerShell scripts for managing SQL Server container and songs database.

## Scripts Overview

### 1. `create-sql-volume.ps1`
Creates a persistent volume directory for SQL container data.

```powershell
.\create-sql-volume.ps1 -containerName "songs-db"
```

**What it does:**
- Creates `~\.sqlcontainers\<name>_<timestamp>` directory
- Creates subdirectories: `data`, `log`, `backup`
- Generates metadata.json file
- Returns volume path for use in docker commands

### 2. `start-songs-db.ps1`
Starts SQL Server container with persistent volume.

```powershell
.\start-songs-db.ps1
.\start-songs-db.ps1 -ContainerName "music-db" -Port 1434
```

**What it does:**
- Creates persistent volume
- Starts SQL Server 2022 container
- Configures port mapping
- Mounts data, log, and backup directories
- Generates secure SA password if not provided
- Saves connection details to `.env.songs-db`
- Tests connection

### 3. `init-songs-db.sql`
SQL script to initialize database schema.

**Creates:**
- Database: `SongsDB`
- Tables: Songs, ProcessingJobs, SeparatedTracks, Transcriptions, ChromaAnalysis, AuditLog
- View: vw_JobSummary
- Stored Procedure: sp_CleanupOldData
- Sample data (optional)

### 4. `setup-songs-db.ps1`
Complete setup script (runs all steps).

```powershell
.\setup-songs-db.ps1
```

**What it does:**
1. Starts SQL Server container
2. Waits for SQL Server to be ready
3. Copies and executes initialization script
4. Verifies database setup
5. Creates Python database connector module
6. Displays connection information

## Quick Start

**Complete setup in one command:**
```powershell
cd scripts
.\setup-songs-db.ps1
```

**Custom setup:**
```powershell
# With custom password
$env:SA_PASSWORD = "MySecureP@ssw0rd!"
.\setup-songs-db.ps1

# With custom container name and port
.\setup-songs-db.ps1 -ContainerName "music-db"
```

## After Setup

### 1. Install Python Dependencies
```bash
pip install pyodbc
```

### 2. Load Environment Variables
```powershell
# PowerShell
. .\.env.songs-db

# Or export to system
Get-Content .env.songs-db | ForEach-Object {
    if ($_ -match '^([^=]+)=(.+)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
```

### 3. Test Python Connection
```bash
python server\songs_db.py
```

### 4. Use in Flask App
```python
from server.songs_db import SongsDatabase

# Initialize
db = SongsDatabase()

# Create song
song_id = db.create_song(
    file_id="abc-123",
    filename="song.mp3",
    title="My Song",
    artist="Artist Name",
    file_size=1024000
)

# Create processing job
job_id = db.create_job(
    song_id=song_id,
    model_name="demucs",
    job_type="separation",
    request_id=request.request_id
)

# Update job status
db.update_job_status(job_id, "completed", progress=100)

# Get song
song = db.get_song("abc-123")

# Log audit
db.log_audit("song", song_id, "created", request_id=request.request_id)
```

## Database Schema

### Songs Table
- Stores uploaded songs and metadata
- Fields: FileId, Title, Artist, FileName, FileSize, Duration, etc.

### ProcessingJobs Table
- Tracks processing jobs (separation, transcription, etc.)
- Fields: JobId, SongId, ModelName, Status, Progress, RequestId

### SeparatedTracks Table
- Stores separated track information
- Fields: TrackName (vocals, drums, bass, other), FilePath, FileSize

### Transcriptions Table
- Stores Whisper transcription results
- Fields: TranscriptionText, Segments, WordTimestamps, Language

### ChromaAnalysis Table
- Stores chroma feature analysis
- Fields: EstimatedKey, EstimatedTempo, ChromaFeatures

### AuditLog Table
- Tracks all operations for debugging
- Fields: RequestId, EntityType, Action, Details

## Management Commands

### Start/Stop Container
```powershell
docker start songs-db
docker stop songs-db
```

### View Logs
```powershell
docker logs songs-db
docker logs -f songs-db  # follow
```

### Connect to SQL Server
```powershell
docker exec -it songs-db /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourPassword' -C
```

### Backup Database
```powershell
# Inside container
docker exec songs-db /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'Password' -C -Q "BACKUP DATABASE SongsDB TO DISK = '/var/opt/mssql/backup/SongsDB.bak'"

# Copy backup out
docker cp songs-db:/var/opt/mssql/backup/SongsDB.bak ./backup/
```

### Remove Container (keeps data)
```powershell
docker stop songs-db
docker rm songs-db

# Data remains in volume directory
# Restart with same volume to restore data
```

## Volume Location

Volumes are stored in: `C:\Users\<username>\.sqlcontainers\`

Each volume directory contains:
- `data/` - Database files (.mdf, .ldf)
- `log/` - Transaction logs
- `backup/` - Database backups
- `metadata.json` - Volume metadata

## Troubleshooting

### Container won't start
```powershell
# Check if port is in use
netstat -ano | findstr :1433

# View container logs
docker logs songs-db
```

### Connection refused
```powershell
# Wait 15-30 seconds for SQL Server to start
Start-Sleep -Seconds 20

# Check if container is running
docker ps | Select-String songs-db

# Test connection
docker exec songs-db /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'Password' -C -Q "SELECT @@VERSION"
```

### Password doesn't meet requirements
SA password must:
- Be at least 8 characters
- Contain uppercase letters
- Contain lowercase letters
- Contain numbers
- Contain special characters

### pyodbc not installed
```bash
pip install pyodbc
```

On Windows, you may also need: [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

## Integration with Backend

### 1. Update Flask App
```python
from server.songs_db import SongsDatabase
from server.logging_utils import setup_flask_app_hooks

app = Flask(__name__)
setup_flask_app_hooks(app)

# Initialize database
db = SongsDatabase()

@app.route('/upload', methods=['POST'])
def upload():
    # ... upload file logic ...
    
    # Save to database
    song_id = db.create_song(
        file_id=file_id,
        filename=stored_filename,
        original_filename=original_filename,
        title=request.form.get('title'),
        artist=request.form.get('artist'),
        file_size=file_size,
        request_id=request.request_id
    )
    
    # Log audit
    db.log_audit('song', song_id, 'uploaded', request_id=request.request_id)
    
    return jsonify({'song_id': song_id, 'file_id': file_id})
```

### 2. Track Processing Jobs
```python
@app.route('/process/<model_name>/<file_id>', methods=['POST'])
def process_file(model_name, file_id):
    song = db.get_song(file_id)
    
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    
    # Create job
    job_id = db.create_job(
        song_id=song['Id'],
        model_name=model_name,
        job_type='separation',
        request_id=request.request_id
    )
    
    # Process asynchronously
    # ... processing logic ...
    
    # Update job status
    db.update_job_status(job_id, 'completed', progress=100)
    
    return jsonify({'job_id': job_id})
```

## Security Notes

- SA password is stored in `.env.songs-db` - keep secure
- Add `.env.songs-db` to `.gitignore`
- Use environment variables in production
- Consider using Azure Key Vault or similar for production passwords
- SQL Server container uses `TrustServerCertificate=yes` for development only

## Production Considerations

For production deployment:
1. Use Azure SQL Database or managed SQL Server
2. Use strong, rotated passwords
3. Enable SSL/TLS with proper certificates
4. Set up automated backups
5. Configure firewall rules
6. Use Azure AD authentication if on Azure
7. Enable auditing and monitoring
8. Use connection pooling

## License

Part of AiMusicSeparator-Backend project.
