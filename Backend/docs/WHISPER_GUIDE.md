# Whisper Speech Recognition - Usage Examples

## Available Whisper Models

Your backend now supports all Whisper models:


## API Usage Examples

### 1. Upload Audio for Speech Recognition

```bash
# Upload audio file for Whisper processing
curl -X POST -F "file=@speech.wav" http://localhost:8000/upload/whisper

# Response:
{
  "file_id": "abc123-def456",
  "filename": "speech.wav", 
  "message": "File uploaded successfully"
}
```

### 2. Process with Whisper

```bash
# Process with default model (base)
curl -X POST http://localhost:8000/process/whisper/abc123-def456

# Process with specific model
curl -X POST -H "Content-Type: application/json" \
  -d '{"model_variant": "small"}' \
  http://localhost:8000/process/whisper/abc123-def456

# Response:
{
  "file_id": "abc123-def456",
  "model": "whisper", 
  "status": "completed",
  "result": {
    "model": "small",
    "transcription": "Hello, this is a test of speech recognition.",
    "language": "en",
    "segments": 1,
    "files": {
      "json": "transcription_small.json",
      "text": "transcription_small.txt"
    }
  }
}
```

### 3. Download Transcription Files

```bash
# Download plain text transcription
curl -O http://localhost:8000/download/whisper/abc123-def456/transcription_small.txt

# Download detailed JSON with timestamps
curl -O http://localhost:8000/download/whisper/abc123-def456/transcription_small.json
```

## PowerShell Examples (Windows)

```powershell
# Upload audio file
$response = Invoke-WebRequest -Uri "http://localhost:8000/upload/whisper" -Method Post -Form @{file = Get-Item "speech.wav"}
$uploadResult = $response.Content | ConvertFrom-Json
$fileId = $uploadResult.file_id

# Process with Whisper
$processResponse = Invoke-WebRequest -Uri "http://localhost:8000/process/whisper/$fileId" -Method Post
$result = $processResponse.Content | ConvertFrom-Json
Write-Host "Transcription: $($result.result.transcription)"

# Download transcription
Invoke-WebRequest -Uri "http://localhost:8000/download/whisper/$fileId/transcription_base.txt" -OutFile "transcription.txt"
```

## Supported Audio Formats

Whisper works with the same audio formats as Demucs:

## Use Cases


## Model Selection Guide

| Model  | Size  | Speed | Use Case |
|--------|-------|-------|----------|
| tiny   | 39MB  | Fastest | Real-time, low accuracy OK |
| base   | 74MB  | Fast | Default, good balance |
| small  | 244MB | Medium | Better accuracy needed |
| medium | 769MB | Slow | High accuracy required |
| large  | 1550MB| Slowest | Best possible accuracy |
| turbo  | 805MB | Fast | New model, good balance |

## Output Files

For each transcription, you get:

1. **Plain text file** (.txt) - Just the transcribed text
2. **JSON file** (.json) - Detailed results with:
   - Full transcription
   - Detected language
   - Word-level timestamps
   - Confidence scores
   - Segment breakdown

Your backend now supports both **Demucs** (audio separation) and **Whisper** (speech recognition)!
NOTE: This file has been moved to the microservices folder.

Canonical microservice copy: `/part of AI separator backend/whisperer/WHISPER_GUIDE.md`

See `/part of AI separator backend/whisperer/README.md` for quick links and examples.