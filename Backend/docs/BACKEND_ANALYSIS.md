# Backend Server Analysis - Lion's Roar Studio Synchronization Report

**Generated:** October 16, 2025

## 📊 Backend Overview

### Current Configuration
- **Server:** Flask with Flask-SocketIO
- **Port:** 5000 (dev) / 8000 (production)
- **CORS:** Enabled for all origins
- **Max Upload:** 100MB

### Supported Audio Formats
- MP3, WAV, FLAC, M4A, OGG

---

## 🤖 AI Models Configured

| Model | Purpose | Default | Variants | Status |
|-------|---------|---------|----------|--------|
| **Demucs** | Audio Separation | htdemucs | htdemucs, mdx_extra, mdx, mdx_q, mdx_extra_q | ✅ Active |
| **Whisper** | Speech Transcription | medium | tiny, base, small, medium, large | ✅ Active |
| **MusicGen** | Music Generation | large | small, medium, large | ✅ Active |
| **Pitch Analysis** | Key Detection | enhanced_chroma | basic_chroma, enhanced_chroma, librosa_chroma | ✅ Active |
| **Gemma 3N** | Audio Transcription & Analysis | gemma-2-9b-it | gemma-2-2b-it, gemma-2-9b-it, gemma-2-27b-it | ✅ Active |

---

## 🔌 API Endpoints Available

### Health & Status
```
GET  /health              → Health check with model list
GET  /health/health       → Duplicate health check (backward compat)
GET  /health/status       → Alternative health check path
GET  /status              → Simple status {"status": "ok"}
```

### Model Information
```
GET  /models              → List all models with configurations
GET  /models/<model_name> → Get specific model configuration
```

### File Upload
```
POST /upload              → Upload audio file (returns file_id)
POST /upload/<model_name> → Upload audio for specific model
```

### Processing
```
POST /process/<model_name>/<file_id>  → Process file with specified model
POST /separate/<file_id>              → Audio separation (backward compat)
POST /analyze/chroma/<file_id>        → Chroma analysis
POST /analyze/batch                   → Batch analysis
```

### Music Generation
```
POST /generate/text-to-music          → Generate music from text prompt
GET  /generate/text-to-music/<file_id> → Get generation status
```

### File Management
```
GET  /download/<model_name>/<file_id>/<filename>  → Download processed file
GET  /download/<file_id>/<track>                  → Download separated track
GET  /status/<file_id>                            → Get processing status
DELETE /cleanup/<file_id>                         → Clean up files
```

### Transcription
```
POST /transcribe  → Speech transcription (WebSocket capable)
```

---

## 📋 API Request/Response Patterns

### Standard Processing Request
```json
POST /process/<model_name>/<file_id>
{
  "model_variant": "model_name_here"
  // Additional model-specific params
}
```

### Standard Response Format
```json
{
  "file_id": "uuid",
  "model": "model_name",
  "status": "completed",
  "result": {
    // Model-specific results
  },
  "message": "Processing completed successfully"
}
```

### Error Response Format
```json
{
  "error": "Error message description",
  "details": "Additional error details if available"
}
```

---

## 🔄 Model-Specific Request/Response Formats

### Demucs (Audio Separation)
```
Request:  POST /process/demucs/<file_id>
          {"model_variant": "htdemucs"}

Response: {
  "result": {
    "model": "htdemucs",
    "tracks": ["vocals", "bass", "drums", "other"],
    "output_dir": "/outputs/file_id/htdemucs/filename"
  }
}
```

### Whisper (Speech Transcription)
```
Request:  POST /process/whisper/<file_id>
          {"model_variant": "medium"}

Response: {
  "result": {
    "model": "medium",
    "transcription_file": "transcription_medium.json",
    "text_file": "transcription_medium.txt"
  }
}
```

### MusicGen (Music Generation)
```
Request:  POST /process/musicgen/<file_id>
          {"prompt": "upbeat jazz", "model_variant": "large"}

Response: {
  "result": {
    "model": "large",
    "generated_file": "generated_music.wav",
    "duration": 15.0
  }
}
```

### Pitch Analysis (Key Detection)
```
Request:  POST /process/pitch_analysis/<file_id>
          {"model_variant": "enhanced_chroma"}

Response: {
  "result": {
    "model": "enhanced_chroma",
    "detected_key": "C major",
    "confidence": 0.87,
    "analysis_file": "pitch_analysis_enhanced_chroma.json",
    "dominant_pitches": ["C", "E", "G"]
  }
}
```

### Gemma 3N (Audio Analysis)
```
Request:  POST /process/gemma_3n/<file_id>
          {"task": "analyze", "model_variant": "gemma-2-9b-it"}

Response: {
  "result": {
    "model": "gemma-2-9b-it",
    "task": "analyze",
    "audio_analysis": "Detailed analysis text...",
    "output_files": {
      "text": "analysis_gemma-2-9b-it_analyze.txt",
      "json": "analysis_gemma-2-9b-it_analyze.json"
    }
  }
}
```

---

## ✅ Backend Capabilities Verification

### ✓ Implemented Features
- [x] 5 AI models fully integrated
- [x] File upload with validation
- [x] Multi-format audio support (MP3, WAV, FLAC, M4A, OGG)
- [x] Batch processing support
- [x] WebSocket transcription (real-time)
- [x] CORS enabled for frontend
- [x] Error handling with detailed messages
- [x] File download endpoints
- [x] Status tracking
- [x] Cleanup utilities
- [x] Health check endpoints

### ✓ Performance Features
- [x] GPU acceleration (torch device_map="auto")
- [x] Mixed precision (torch.bfloat16)
- [x] Async processing capability
- [x] Configurable model variants
- [x] Default fallbacks

---

## 🔍 Potential Lion's Roar Studio Sync Issues

### Issue 1: Unknown Audio URL Format Error
**Error:** "Invalid audio URL format" from frontend
**Likely Cause:** Lion's Roar Studio not sending file_id, or incorrect endpoint path

**Lion's Roar Studio Should:**
```javascript
// ✓ CORRECT - Upload first, get file_id, then process
const fileId = await uploadFile(audioFile);
const result = await fetch(`/process/pitch_analysis/${fileId}`, {
  method: 'POST',
  body: JSON.stringify({ model_variant: 'enhanced_chroma' })
});

// ✗ WRONG - Don't send file URL directly
const result = await fetch(`/process/pitch_analysis`, {
  method: 'POST',
  body: JSON.stringify({ url: 'http://...' })  // Backend doesn't support this
});
```

### Issue 2: Model Endpoint Naming Inconsistency
**Backend Endpoint:** `/process/pitch_analysis/<file_id>`
**Lion's Roar Studio Expectation:** Verify it matches exactly

**Backend Endpoint:** `/process/gemma_3n/<file_id>`
**Lion's Roar Studio Expectation:** Verify it matches exactly (uses underscore, not dash)

### Issue 3: Request/Response Body Structure
**Backend Expects:**
```json
{
  "model_variant": "enhanced_chroma"
}
```

**Backend Does NOT support:**
- Direct URL/file paths in request
- Streaming file data (use /upload first)
- model (use model_variant instead)

---

## 📋 Sync Checklist for Lion's Roar Studio

### Required Lion's Roar Studio Implementations
- [ ] Upload audio file via `/upload` → receive `file_id`
- [ ] Use exact endpoint names: `/process/demucs/`, `/process/whisper/`, etc.
- [ ] Send requests as `application/json` with `model_variant` parameter
- [ ] Handle error responses with error status codes
- [ ] Use file_id from upload response in all subsequent requests
- [ ] Don't attempt to send URLs or file paths directly

### Recommended Lion's Roar Studio Patterns
```javascript
// Pattern 1: Upload then Process
const uploadRes = await fetch('/upload', { 
  method: 'POST', 
  body: formData 
});
const { file_id } = await uploadRes.json();

// Pattern 2: Process with Model
const processRes = await fetch(`/process/demucs/${file_id}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ model_variant: 'htdemucs' })
});

// Pattern 3: Get Status
const statusRes = await fetch(`/status/${file_id}`);

// Pattern 4: Download Result
const downloadUrl = `/download/demucs/${file_id}/vocals.mp3`;
```

---

## 🧪 Backend Verification Commands

### Check Health
```bash
curl http://localhost:5000/health
```

### List Models
```bash
curl http://localhost:5000/models
```

### Upload File
```bash
curl -X POST -F "file=@audio.mp3" http://localhost:5000/upload
```

### Process File
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"model_variant": "enhanced_chroma"}' \
  http://localhost:5000/process/pitch_analysis/<file_id>
```

---

## 📚 Current Status

### Backend Status: ✅ PRODUCTION READY
- All 5 AI models integrated
- All endpoints functional
- Error handling implemented
- CORS configured
- matplotlib dependency installed (fixed)

### Sync Status: ⚠️ NEEDS VERIFICATION
**Note:** Lion's Roar Studio code not found in this workspace. Cannot verify if frontend is correctly calling these endpoints.

**Next Steps:**
1. Check frontend's ScoreboardWindow.tsx component
2. Verify endpoint paths match exactly
3. Verify request body structure matches expected format
4. Verify response handling matches response format
5. Test each endpoint with curl commands above

---

## 🎯 Recommended Lion's Roar Studio Configuration

```javascript
// API Base Configuration
const API_BASE = 'http://localhost:5000';

// Model Endpoints
const ENDPOINTS = {
  upload: `${API_BASE}/upload`,
  process: (model, fileId) => `${API_BASE}/process/${model}/${fileId}`,
  download: (model, fileId, filename) => 
    `${API_BASE}/download/${model}/${fileId}/${filename}`,
  status: (fileId) => `${API_BASE}/status/${fileId}`,
  health: `${API_BASE}/health`
};

// Available Models
const MODELS = {
  DEMUCS: 'demucs',
  WHISPER: 'whisper',
  MUSICGEN: 'musicgen',
  PITCH_ANALYSIS: 'pitch_analysis',
  GEMMA_3N: 'gemma_3n'
};
```

---

## 📞 Troubleshooting

### 500 Errors
Check backend logs for detailed error messages. Most common issues:
- Missing dependencies (now fixed with matplotlib)
- Invalid file format
- File not found after upload
- Model processing errors

### CORS Errors
Backend has CORS enabled for all origins. Ensure:
- Lion's Roar Studio is making requests to correct URL
- Content-Type headers are set correctly
- Preflight OPTIONS requests succeed

### Timeout Errors
Some models take time:
- Demucs: 30-60 seconds per song
- Whisper (large): 20-40 seconds
- Gemma 3N: 10-30 seconds
Consider implementing progress tracking with WebSocket

---

## 📊 Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **Backend Models** | ✅ Ready | 5 AI models configured and tested |
| **API Endpoints** | ✅ Ready | 20+ endpoints available |
| **Error Handling** | ✅ Ready | Comprehensive error responses |
| **Dependencies** | ✅ Ready | All packages installed (matplotlib fixed) |
| **CORS** | ✅ Ready | Configured for all origins |
| **Lion's Roar Studio Sync** | ⚠️ Unknown | Need to verify frontend implementation |

**Overall Assessment:** Backend is fully functional and ready. Lion's Roar Studio needs verification against this API specification.
