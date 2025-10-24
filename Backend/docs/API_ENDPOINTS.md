# 🎯 API Endpoints Reference

Complete list of all API endpoints in the AI Music Separator AI separator backend with 5 AI models.

## 📊 Core Endpoints

### Health Check
```bash
GET /health
# Response: {"status": "ok", "models": {...}}
```

### Status
```bash
GET /status
# Response: {"status": "ok"}
```

### Available Models
```bash
GET /models
# Response: {"demucs": {...}, "whisper": {...}, "musicgen": {...}, 
#            "pitch_analysis": {...}, "gemma_3n": {...}}
```

---

## 🎶 1. Audio Separation (Demucs)

### Separate Audio
```bash
POST /process/demucs/<file_id>
Content-Type: application/json

{
  "model_variant": "htdemucs"
}

# Response:
{
  "model": "htdemucs",
  "tracks": ["vocals", "bass", "drums", "other"],
  "output_dir": "/outputs/file_id/htdemucs/filename"
}
```

### Legacy Endpoints (Backward Compatibility)
```bash
# Upload
POST /upload
# Input: file

# Separate
POST /separate/<file_id>

# Download
GET /download/demucs/<file_id>/<track>.mp3
```

---

## 🎤 2. Speech Transcription (Whisper)

### Transcribe Audio
```bash
POST /process/whisper/<file_id>
Content-Type: application/json

{
  "model_variant": "medium"
}

# Response:
{
  "model": "medium",
  "transcription_file": "transcription_medium.json",
  "text_file": "transcription_medium.txt",
  "output_dir": "/outputs/file_id"
}
```

### Models Available
- `tiny` - Fastest
- `base` - Default
- `small` - Better accuracy
- `medium` - High accuracy
- `large` - Highest accuracy

---

## 🎼 3. Music Generation (MusicGen)

### Generate Music
```bash
POST /process/musicgen/<session_id>
Content-Type: application/json

{
  "prompt": "upbeat jazz piano solo",
  "model_variant": "large",
  "duration": 10,
  "temperature": 1.0,
  "cfg_coeff": 3.0
}

# Response:
{
  "model": "large",
  "prompt": "upbeat jazz piano solo",
  "generated_file": "generated_large.wav",
  "duration": 10,
  "sample_rate": 32000,
  "output_dir": "/outputs/session_id"
}
```

### Models Available
- `small` - Fast generation
- `medium` - Better quality
- `large` ⭐ Default - Highest quality

---

## 🎹 4. Pitch & Key Analysis

### Analyze Pitch and Key
```bash
POST /process/pitch_analysis/<file_id>
Content-Type: application/json

{
  "model_variant": "enhanced_chroma"
}

# Response:
{
  "model": "enhanced_chroma",
  "detected_key": "C major",
  "confidence": 0.85,
  "dominant_pitches": ["C", "G", "E"],
  "analysis_file": "pitch_analysis_enhanced_chroma.json",
  "output_dir": "/outputs/file_id"
}
```

### Models Available
- `basic_chroma` - Simple analysis
- `enhanced_chroma` ⭐ Default - Advanced features
- `librosa_chroma` - Comprehensive analysis

---

## 🤖 5. Audio Transcription & Analysis (Gemma 3N) ⭐ NEW

### Transcribe Audio
```bash
POST /process/gemma_3n/<file_id>
Content-Type: application/json

{
  "task": "transcribe",
  "model_variant": "gemma-2-9b-it"
}

# Response:
{
  "model": "gemma-2-9b-it",
  "task": "transcribe",
  "filename": "audio.mp3",
  "duration_seconds": 45.2,
  "sample_rate": 44100,
  "audio_features": {
    "rms_energy": 0.125,
    "spectral_centroid_hz": 2450.3,
    "zero_crossing_rate": 0.045
  },
  "transcription": "Detailed audio transcription...",
  "output_text_file": "analysis_gemma-2-9b-it_transcribe.txt",
  "output_json_file": "analysis_gemma-2-9b-it_transcribe.json"
}
```

### Analyze Audio
```bash
POST /process/gemma_3n/<file_id>
Content-Type: application/json

{
  "task": "analyze",
  "model_variant": "gemma-2-9b-it",
  "temperature": 0.7,
  "top_p": 0.9
}

# Response:
{
  "model": "gemma-2-9b-it",
  "task": "analyze",
  "filename": "audio.mp3",
  "audio_analysis": "Technical audio analysis with extracted features...",
  "output_text_file": "analysis_gemma-2-9b-it_analyze.txt",
  "output_json_file": "analysis_gemma-2-9b-it_analyze.json"
}
```

### Models Available
- `gemma-2-2b-it` - Lightweight (9GB)
- `gemma-2-9b-it` ⭐ Default - Balanced (18GB)
- `gemma-2-27b-it` - High quality (40GB)

### Audio Analysis Parameters
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `task` | string | required | Task: `transcribe` or `analyze` |
| `model_variant` | string | gemma-2-9b-it | Model to use |
| `temperature` | 0.1-2.0 | 0.7 | Generation randomness |
| `top_p` | 0.0-1.0 | 0.9 | Nucleus sampling diversity |
| `do_sample` | boolean | true | Use sampling vs greedy |

---

## 🔌 WebSocket API

### Real-time Transcription
```javascript
// Connect to WebSocket
const socket = io('http://localhost:5000/transcribe');

// Start transcription
socket.emit('start_transcription', {
  file_id: 'your-file-id',
  model: 'base'
});

// Receive results
socket.on('transcription_result', (data) => {
  console.log('Transcription:', data);
});
```

---

### GET /gpu-status

Lightweight endpoint to report PyTorch/CUDA availability and GPU devices. This endpoint intentionally avoids loading large models and is intended for frontend pre-flight checks.

Response (200):

```json
{
  "available": true,
  "torch_installed": true,
  "torch_version": "2.3.0",
  "cuda_available": true,
  "gpu_count": 1,
  "devices": ["NVIDIA GeForce RTX 5070 Ti"]
}
```

If PyTorch is not installed the endpoint will return:

```json
{ "available": false, "torch_installed": false }
```

Client guidance:
- Call `/gpu-status` before issuing heavy `/process/*` requests (Whisper, Demucs, MusicGen, Gemma).
- If `available` is false, do not send heavy jobs; the backend enforces GPU-only and will return HTTP 503 for such requests.


---

## 🛠️ Error Handling

### Common Error Responses

**400 Bad Request** - Missing or invalid parameters
```json
{
  "error": "Missing required parameter: prompt"
}
```

**415 Unsupported Media Type** - Wrong Content-Type header
```json
{
  "error": "Unsupported Media Type. Use application/json"
}
```

**500 Internal Server Error** - Processing failed
```json
{
  "error": "Model processing failed: [error details]"
}
```

---

## 📋 Request Header Examples

### JSON Requests
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"task": "transcribe", "model_variant": "gemma-2-9b-it"}' \
  http://localhost:5000/process/gemma_3n/file_id
```

### File Upload
```bash
curl -X POST \
  -F "file=@audio.mp3" \
  http://localhost:5000/process/demucs
```

---

## 🔐 CORS Support

All endpoints support CORS. Lion's Roar Studio can request from:
- `http://localhost:3000`
- `http://localhost:5173`
- Any configured origin in `.env`

---

## 📊 Response Format Standards

All successful responses follow this format:
```json
{
  "model": "model_name",
  "status": "success",
  "result": {
    // Model-specific result data
  },
  "output_dir": "/outputs/session_id",
  "timestamp": "2025-10-16T10:30:45"
}
```

---

## 🚀 Usage Examples

### Example 1: Complete Audio Processing Pipeline
```bash
# 1. Upload audio
curl -X POST -F "file=@song.mp3" http://localhost:5000/upload
# Response: {"file_id": "abc123"}

# 2. Separate vocals
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"model_variant": "htdemucs"}' \
  http://localhost:5000/process/demucs/abc123

# 3. Transcribe vocals
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"model_variant": "medium"}' \
  http://localhost:5000/process/whisper/abc123

# 4. Analyze pitch
curl -X POST http://localhost:5000/process/pitch_analysis/abc123
```

### Example 2: Audio Transcription with Gemma 3N
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "task": "transcribe",
    "model_variant": "gemma-2-9b-it"
  }' \
  http://localhost:5000/process/gemma_3n/abc123
```

### Example 3: Audio Analysis with Gemma 3N
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "task": "analyze",
    "model_variant": "gemma-2-9b-it",
    "temperature": 0.7
  }' \
  http://localhost:5000/process/gemma_3n/abc123
```

### Example 4: Generate Music
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "lo-fi hip hop beats with chill vibes",
    "duration": 30,
    "model_variant": "large"
  }' \
  http://localhost:5000/process/musicgen/music_001
```

---

## 📚 Documentation Links

- [README.md](./README.md) - Project overview
- [GEMMA_3N_GUIDE.md](/part of Backend/gemma3n/GEMMA_3N_GUIDE.md) - Gemma 3N detailed guide
- [COMPLETE_GUIDE.md](./COMPLETE_GUIDE.md) - Comprehensive setup guide
- [WHISPER_GUIDE.md](/part of Backend/whisperer/WHISPER_GUIDE.md) - Transcription guide
- [MUSICGEN_GUIDE.md](/part of Backend/musicgen/MUSICGEN_GUIDE.md) - Music generation guide (canonical)
- [HTTPS_DEPLOYMENT.md](./HTTPS_DEPLOYMENT.md) - HTTPS setup

---

**All 5 AI Models Ready! 🚀**
