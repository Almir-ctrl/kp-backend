-- Initialize Songs Database for AiMusicSeparator
-- This script creates the database schema for storing songs, metadata, and processing results

USE master;
GO

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'SongsDB')
BEGIN
    CREATE DATABASE SongsDB;
    PRINT 'Database SongsDB created successfully.';
END
ELSE
BEGIN
    PRINT 'Database SongsDB already exists.';
END
GO

USE SongsDB;
GO

-- Table: Songs
-- Stores uploaded songs and their metadata
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Songs')
BEGIN
    CREATE TABLE Songs (
        Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        FileId NVARCHAR(100) NOT NULL UNIQUE,
        Title NVARCHAR(255),
        Artist NVARCHAR(255),
        Album NVARCHAR(255),
        FileName NVARCHAR(500) NOT NULL,
        OriginalFileName NVARCHAR(500),
        FileSize BIGINT,
        Duration FLOAT,
        FileExtension NVARCHAR(10),
        MimeType NVARCHAR(100),
        UploadedAt DATETIME2 DEFAULT GETUTCDATE(),
        LastModified DATETIME2 DEFAULT GETUTCDATE(),
        Metadata NVARCHAR(MAX), -- JSON metadata
        Status NVARCHAR(50) DEFAULT 'uploaded',
        CreatedBy NVARCHAR(100),
        INDEX IX_Songs_FileId (FileId),
        INDEX IX_Songs_Status (Status),
        INDEX IX_Songs_UploadedAt (UploadedAt)
    );
    PRINT 'Table Songs created successfully.';
END
GO

-- Table: ProcessingJobs
-- Tracks processing jobs for separation, transcription, etc.
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ProcessingJobs')
BEGIN
    CREATE TABLE ProcessingJobs (
        Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        JobId NVARCHAR(100) NOT NULL UNIQUE,
        SongId UNIQUEIDENTIFIER NOT NULL,
        ModelName NVARCHAR(100) NOT NULL,
        JobType NVARCHAR(50) NOT NULL, -- 'separation', 'transcription', 'chroma', etc.
        Status NVARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
        Progress FLOAT DEFAULT 0,
        Message NVARCHAR(MAX),
        RequestId NVARCHAR(100), -- X-Request-ID for tracing
        StartedAt DATETIME2,
        CompletedAt DATETIME2,
        CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
        ErrorMessage NVARCHAR(MAX),
        ErrorStack NVARCHAR(MAX),
        ResultMetadata NVARCHAR(MAX), -- JSON results
        FOREIGN KEY (SongId) REFERENCES Songs(Id) ON DELETE CASCADE,
        INDEX IX_Jobs_JobId (JobId),
        INDEX IX_Jobs_SongId (SongId),
        INDEX IX_Jobs_Status (Status),
        INDEX IX_Jobs_RequestId (RequestId)
    );
    PRINT 'Table ProcessingJobs created successfully.';
END
GO

-- Table: SeparatedTracks
-- Stores information about separated audio tracks
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'SeparatedTracks')
BEGIN
    CREATE TABLE SeparatedTracks (
        Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        JobId UNIQUEIDENTIFIER NOT NULL,
        SongId UNIQUEIDENTIFIER NOT NULL,
        TrackName NVARCHAR(100) NOT NULL, -- 'vocals', 'drums', 'bass', 'other'
        FileName NVARCHAR(500) NOT NULL,
        FilePath NVARCHAR(1000) NOT NULL,
        FileSize BIGINT,
        Duration FLOAT,
        FileExtension NVARCHAR(10),
        CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
        Metadata NVARCHAR(MAX), -- JSON metadata
        FOREIGN KEY (JobId) REFERENCES ProcessingJobs(Id) ON DELETE CASCADE,
        FOREIGN KEY (SongId) REFERENCES Songs(Id) ON DELETE CASCADE,
        INDEX IX_Tracks_JobId (JobId),
        INDEX IX_Tracks_SongId (SongId),
        INDEX IX_Tracks_TrackName (TrackName)
    );
    PRINT 'Table SeparatedTracks created successfully.';
END
GO

-- Table: Transcriptions
-- Stores transcription results from Whisper
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Transcriptions')
BEGIN
    CREATE TABLE Transcriptions (
        Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        JobId UNIQUEIDENTIFIER NOT NULL,
        SongId UNIQUEIDENTIFIER NOT NULL,
        TranscriptionText NVARCHAR(MAX),
        Language NVARCHAR(10),
        Segments NVARCHAR(MAX), -- JSON array of timed segments
        WordTimestamps NVARCHAR(MAX), -- JSON array of word-level timestamps
        Confidence FLOAT,
        ModelUsed NVARCHAR(100),
        CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
        FOREIGN KEY (JobId) REFERENCES ProcessingJobs(Id) ON DELETE CASCADE,
        FOREIGN KEY (SongId) REFERENCES Songs(Id) ON DELETE CASCADE,
        INDEX IX_Transcriptions_JobId (JobId),
        INDEX IX_Transcriptions_SongId (SongId)
    );
    PRINT 'Table Transcriptions created successfully.';
END
GO

-- Table: ChromaAnalysis
-- Stores chroma feature analysis results
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ChromaAnalysis')
BEGIN
    CREATE TABLE ChromaAnalysis (
        Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        JobId UNIQUEIDENTIFIER NOT NULL,
        SongId UNIQUEIDENTIFIER NOT NULL,
        EstimatedKey NVARCHAR(10),
        EstimatedKeyConfidence FLOAT,
        EstimatedTempo FLOAT,
        ChromaFeatures NVARCHAR(MAX), -- JSON array of chroma features
        KeyProfile NVARCHAR(MAX), -- JSON key profile
        AnalysisMetadata NVARCHAR(MAX), -- JSON metadata
        CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
        FOREIGN KEY (JobId) REFERENCES ProcessingJobs(Id) ON DELETE CASCADE,
        FOREIGN KEY (SongId) REFERENCES Songs(Id) ON DELETE CASCADE,
        INDEX IX_Chroma_JobId (JobId),
        INDEX IX_Chroma_SongId (SongId)
    );
    PRINT 'Table ChromaAnalysis created successfully.';
END
GO

-- Table: AuditLog
-- Tracks all operations for debugging and monitoring
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'AuditLog')
BEGIN
    CREATE TABLE AuditLog (
        Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        RequestId NVARCHAR(100),
        EntityType NVARCHAR(50), -- 'song', 'job', 'track', etc.
        EntityId NVARCHAR(100),
        Action NVARCHAR(50), -- 'created', 'updated', 'deleted', 'processed'
        UserId NVARCHAR(100),
        IpAddress NVARCHAR(50),
        UserAgent NVARCHAR(500),
        Details NVARCHAR(MAX), -- JSON details
        Timestamp DATETIME2 DEFAULT GETUTCDATE(),
        INDEX IX_Audit_RequestId (RequestId),
        INDEX IX_Audit_EntityType (EntityType),
        INDEX IX_Audit_Timestamp (Timestamp)
    );
    PRINT 'Table AuditLog created successfully.';
END
GO

-- Create view for job summary
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_JobSummary')
BEGIN
    EXEC('
    CREATE VIEW vw_JobSummary AS
    SELECT 
        j.JobId,
        j.JobType,
        j.ModelName,
        j.Status,
        j.Progress,
        j.RequestId,
        j.CreatedAt,
        j.StartedAt,
        j.CompletedAt,
        DATEDIFF(SECOND, j.StartedAt, COALESCE(j.CompletedAt, GETUTCDATE())) AS DurationSeconds,
        s.FileId,
        s.Title,
        s.Artist,
        s.FileName
    FROM ProcessingJobs j
    INNER JOIN Songs s ON j.SongId = s.Id
    ');
    PRINT 'View vw_JobSummary created successfully.';
END
GO

-- Create stored procedure to clean up old data
IF NOT EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_CleanupOldData')
BEGIN
    EXEC('
    CREATE PROCEDURE sp_CleanupOldData
        @DaysToKeep INT = 30
    AS
    BEGIN
        SET NOCOUNT ON;
        
        DECLARE @CutoffDate DATETIME2 = DATEADD(DAY, -@DaysToKeep, GETUTCDATE());
        
        -- Delete old audit logs
        DELETE FROM AuditLog WHERE Timestamp < @CutoffDate;
        
        -- Delete completed jobs older than cutoff
        DELETE FROM ProcessingJobs 
        WHERE Status = ''completed'' 
        AND CompletedAt < @CutoffDate;
        
        -- Note: Songs are not auto-deleted; manual cleanup required
        
        SELECT 
            ''Cleanup completed'' AS Message,
            @@ROWCOUNT AS RecordsDeleted,
            @CutoffDate AS CutoffDate;
    END
    ');
    PRINT 'Stored procedure sp_CleanupOldData created successfully.';
END
GO

-- Insert sample data for testing (optional)
IF NOT EXISTS (SELECT * FROM Songs)
BEGIN
    PRINT 'Inserting sample data...';
    
    INSERT INTO Songs (FileId, Title, Artist, FileName, OriginalFileName, FileSize, Status)
    VALUES 
        ('sample-001', 'Test Song 1', 'Test Artist', 'sample-001.mp3', 'test1.mp3', 1024000, 'uploaded'),
        ('sample-002', 'Test Song 2', 'Test Artist', 'sample-002.wav', 'test2.wav', 2048000, 'uploaded');
    
    PRINT 'Sample data inserted.';
END
GO

PRINT '';
PRINT '=== Database Initialization Complete ===';
PRINT 'Database: SongsDB';
PRINT 'Tables: Songs, ProcessingJobs, SeparatedTracks, Transcriptions, ChromaAnalysis, AuditLog';
PRINT 'Views: vw_JobSummary';
PRINT 'Procedures: sp_CleanupOldData';
GO
