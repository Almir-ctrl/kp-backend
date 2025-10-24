# MusicGen Text-to-Music Generation

NOTE: This file has been moved to the microservices folder.

Canonical microservice copy: `/part of AI separator backend/musicgen/MUSICGEN_GUIDE.md`

See `/part of AI separator backend/musicgen/README.md` for quick links and usage examples.

## Features

- **Text-to-Music Generation**: Create music from descriptive text prompts
- **Multiple Model Variants**: Support for `small`, `medium`, and `large` MusicGen models
- **Configurable Parameters**: Control duration, temperature, and CFG coefficient
- **Mock Fallback**: Works even when AudioCraft isn't installed (generates placeholder audio)
- **REST API**: Easy integration with web applications

## API Endpoints

### 1. Generate Music from Text

**POST** `/generate/text-to-music`

Generate music from a text prompt.

#### Request Body
```json
{
    "prompt": "upbeat electronic dance music with synthesizers and drums",
    "model_variant": "small",  // Optional: "small", "medium", "large" 
    "duration": 15,            // Optional: 1-120 seconds
    "temperature": 1.0,        // Optional: 0.1-2.0 (creativity)
    "cfg_coeff": 3.0          // Optional: 1.0-10.0 (prompt adherence)
}
```

#### Response
```json
{
    "file_id": "uuid-string",
    "model": "musicgen",
    "prompt": "upbeat electronic dance music...",
    "status": "completed",
    "result": {
        "model": "small",
        "prompt": "upbeat electronic dance music...",
        "generated_file": "generated_small.wav",
        "duration": 15,
        "sample_rate": 32000,
        "file_size_mb": 2.34
    },
    "message": "Music generation completed successfully",
    "download_url": "/download/{file_id}/generated_small.wav"
}
```

### 2. Check Generation Status

**GET** `/generate/text-to-music/{file_id}`

Check the status of a music generation request.

#### Response
```json
{
    "file_id": "uuid-string",
    "status": "completed",
    "generated_files": [
        {
            "filename": "generated_small.wav",
            "size_mb": 2.34,
            "download_url": "/download/{file_id}/generated_small.wav"
        }
    ],
    "prompt_info": {
        "prompt": "upbeat electronic dance music...",
        "model": "small",
        "duration": "15s",
        "temperature": "1.0",
        "cfg coefficient": "3.0"
    },
    "total_files": 1
}
```

### 3. Download Generated Music

**GET** `/download/{file_id}/{filename}`

Download the generated audio file.

## Usage Examples

### Python Example

```python
import requests

# Generate music
response = requests.post('http://localhost:5000/generate/text-to-music', json={
    "prompt": "peaceful ambient music with soft piano and nature sounds",
    "duration": 30,
    "model_variant": "medium"
})

if response.status_code == 200:
    result = response.json()
    file_id = result['file_id']
    
    # Download the generated music
    download_url = f"http://localhost:5000{result['download_url']}"
    audio_response = requests.get(download_url)
    
    with open(f"generated_music_{file_id}.wav", "wb") as f:
        f.write(audio_response.content)
    
    print(f"Music saved as generated_music_{file_id}.wav")
```

### JavaScript Example

```javascript
// Generate music
const response = await fetch('http://localhost:5000/generate/text-to-music', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        prompt: "energetic rock music with electric guitar solos",
        duration: 20,
        model_variant: "large",
        temperature: 1.2
    })
});

if (response.ok) {
    const result = await response.json();
    console.log('Generation completed:', result);
    
    // The audio can be downloaded from result.download_url
    const audioUrl = `http://localhost:5000${result.download_url}`;
    console.log('Download audio from:', audioUrl);
}
```

### cURL Example

```bash
# Generate music
curl -X POST http://localhost:5000/generate/text-to-music \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "classical violin concerto in a major key",
    "duration": 25,
    "model_variant": "medium",
    "temperature": 0.8,
    "cfg_coeff": 4.0
  }'

# Check status
curl http://localhost:5000/generate/text-to-music/{file_id}

# Download generated music
curl -O http://localhost:5000/download/{file_id}/generated_medium.wav
```

## Parameters Guide

### Model Variants
- **small**: Fastest generation, good quality
- **medium**: Balanced speed and quality  
- **large**: Highest quality, slower generation

### Temperature (0.1 - 2.0)
- **Low (0.1-0.7)**: More predictable, conservative output
- **Medium (0.8-1.2)**: Balanced creativity
- **High (1.3-2.0)**: More creative and diverse output

### CFG Coefficient (1.0 - 10.0)
- **Low (1.0-3.0)**: More creative freedom
- **Medium (3.0-6.0)**: Balanced prompt adherence
- **High (6.0-10.0)**: Strict prompt following

### Duration
- Minimum: 1 second
- Maximum: 120 seconds (2 minutes)
- Recommended: 10-30 seconds for best results

## Prompt Writing Tips

### Good Prompts
- "upbeat electronic dance music with synthesizers and heavy bass"
- "peaceful acoustic guitar ballad in minor key"
- "jazz piano trio with walking bass line"
- "orchestral film score with strings and brass"
- "ambient soundscape with ethereal pads and gentle percussion"

### Prompt Structure
1. **Genre/Style**: "electronic", "classical", "jazz", "rock"
2. **Instruments**: "piano", "guitar", "violin", "synthesizer"
3. **Mood/Energy**: "upbeat", "peaceful", "dramatic", "melancholic"
4. **Additional Details**: "in major key", "with heavy drums", "slow tempo"

## Installation

### With AudioCraft (Full Features)
```bash
pip install audiocraft transformers torch torchaudio
```

### Fallback Mode (Mock Generation)
If AudioCraft installation fails (common on Windows), the system will automatically use a mock implementation that generates placeholder audio.

```bash
pip install transformers torch torchaudio
```

## Configuration

The MusicGen configuration is defined in `config.py`:

```python
'musicgen': {
    'default_model': 'small',
    'available_models': ['small', 'medium', 'large'],
    'purpose': 'music_generation',
    'file_types': {'txt'}
}
```

## Error Handling

### Common Errors

1. **Empty Prompt**
   ```json
   {"error": "Empty text prompt provided"}
   ```

2. **Invalid Duration**
   ```json
   {"error": "Duration must be between 1 and 120 seconds"}
   ```

3. **Invalid Temperature**
   ```json
   {"error": "Temperature must be between 0.1 and 2.0"}
   ```

4. **AudioCraft Not Available**
   - System automatically falls back to mock implementation
   - Generates placeholder sine wave audio
   - Logs: "AudioCraft not available, using mock MusicGen"

## Integration with Other Models

MusicGen works alongside other AI models in the backend:

- **Demucs**: Audio source separation
- **Whisper**: Speech-to-text transcription  
- **Enhanced Chroma Analysis**: Music analysis with Librosa

All models share the same REST API structure and can be used together for comprehensive audio processing workflows.

## File Structure

Generated files are organized as:
```
outputs/
└── {file_id}/
    ├── generated_{model_variant}.wav  # Generated audio
    └── prompt_{model_variant}.txt     # Generation metadata
```

## Performance Notes

- **Small Model**: ~2-3 seconds generation time for 15s audio
- **Medium Model**: ~5-8 seconds generation time for 15s audio  
- **Large Model**: ~10-15 seconds generation time for 15s audio

Generation times depend on:
- Hardware (GPU vs CPU)
- Audio duration
- Model variant
- System load

## Production Deployment

For production use:
1. Install AudioCraft on a system with proper compilation tools
2. Use GPU acceleration for faster generation
3. Implement request queuing for high load
4. Monitor disk space for generated files
5. Set up automatic cleanup of old generated files

The mock fallback ensures the API works even in constrained environments where AudioCraft compilation fails.