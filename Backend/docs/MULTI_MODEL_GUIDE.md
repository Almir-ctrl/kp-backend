# Multi-Model AI AI separator backend Examples

## Available Models

Your backend now supports multiple AI models for different purposes:

### 1. Demucs (Audio Separation)
**Purpose**: Separate audio into individual tracks (vocals, drums, bass, other)

```bash
# Upload audio file for Demucs
curl -X POST -F "file=@song.mp3" http://localhost:8000/upload/demucs

# Process with default model (htdemucs)
curl -X POST http://localhost:8000/process/demucs/your-file-id

# Process with specific model variant
curl -X POST -H "Content-Type: application/json" \
  -d '{"model_variant": "mdx_extra"}' \
  http://localhost:8000/process/demucs/your-file-id
```

### 2. Whisper (Speech-to-Text) [Example - Not Implemented]
**Purpose**: Convert speech/audio to text transcription

```bash
# Upload audio file for Whisper
curl -X POST -F "file=@speech.wav" http://localhost:5000/upload/whisper

# Process with default model
curl -X POST http://localhost:5000/process/whisper/your-file-id

# Process with specific model size
curl -X POST -H "Content-Type: application/json" \
  -d '{"model_variant": "large"}' \
  http://localhost:5000/process/whisper/your-file-id
```

### 3. MusicGen (Text-to-Music) [Example - Not Implemented]
**Purpose**: Generate music from text descriptions

```bash
# Upload text file with music description
curl -X POST -F "file=@description.txt" http://localhost:5000/upload/musicgen

# Process with prompt
curl -X POST -H "Content-Type: application/json" \
  -d '{"model_variant": "medium", "prompt": "upbeat electronic dance music"}' \
  http://localhost:5000/process/musicgen/your-file-id
```

## API Endpoints

### Model Information
```bash
# List all available models
GET /models

# Get specific model info
GET /models/demucs
GET /models/whisper
GET /models/musicgen
```

### File Processing
```bash
# Generic upload (defaults to demucs)
POST /upload

# Model-specific upload
POST /upload/{model_name}

# Process with specific model
POST /process/{model_name}/{file_id}

# Backward compatibility (demucs only)
POST /separate/{file_id}
```

## Adding New Models

To add a new model:

1. **Update `config.py`** - Add model configuration
2. **Create processor** in `models.py` - Implement processing logic
3. **Register processor** - Add to PROCESSORS dict

### Example: Adding a Voice Cloning Model

```python
# In config.py
'voice_clone': {
    'default_model': 'tacotron2',
    'available_models': ['tacotron2', 'waveglow'],
    'purpose': 'voice_synthesis',
    'file_types': {'wav', 'mp3'}
}

# In models.py
class VoiceCloneProcessor(ModelProcessor):
    def process(self, file_id, input_file, model_variant=None, target_voice=None):
        # Implement voice cloning logic
        pass

# Register it
PROCESSORS['voice_clone'] = VoiceCloneProcessor
```

## Benefits of Multi-Model Architecture

✅ **Modular Design** - Easy to add/remove models
✅ **Consistent API** - Same endpoints for all models  
✅ **Flexible Processing** - Model-specific parameters
✅ **Backward Compatibility** - Existing endpoints still work
✅ **Scalable** - Each model can have different configurations
NOTE: This file has been moved to the microservices folder.

Canonical microservice copy: `/part of AI separator backend/demucs/MULTI_MODEL_GUIDE.md` (now the canonical location)

See `/part of AI separator backend/demucs/README.md` for quick links and usage examples.