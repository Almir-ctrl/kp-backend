# 🎯 Gemma 3N Audio Transcription & Analysis Guide

NOTE: This file has been moved to the microservices folder.

Canonical microservice copy: `/part of AI separator backend/gemma3n/GEMMA_3N_GUIDE.md`

See `/part of AI separator backend/gemma3n/README.md` for quick links and usage examples.

## Features

- **Audio Transcription**: Generate detailed transcriptions of audio content
- **Audio Analysis**: Extract and analyze audio characteristics (MFCC, spectral features, etc.)
- **Multiple Model Sizes**: 2B, 9B, and 27B parameter models
- **Instruction Tuned**: Optimized for following commands and generating structured output
- **GPU Accelerated**: Fast inference with torch.bfloat16 precision

## Installation

### Prerequisites

```bash
# Ensure required packages are installed
pip install transformers torch librosa soundfile
```

### Install Gemma 3N Dependencies

```bash
pip install -r requirements.txt
# or for production
pip install -r requirements-prod.txt
```

Required packages:
- `transformers` - Hugging Face transformer library
- `torch` - PyTorch deep learning framework
- `librosa` - Audio analysis and feature extraction
- `soundfile` - Audio file I/O

## Quick Start

### 1. Start the Server

```bash
python app.py
```

Server runs on `http://localhost:5000`

### 2. Transcribe Audio

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"task": "transcribe"}' \
  "http://localhost:5000/process/gemma_3n/session_001"
```

### 3. Analyze Audio

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"task": "analyze"}' \
  "http://localhost:5000/process/gemma_3n/session_001"
```

## API Documentation

### Transcribe & Analyze Endpoint

**POST** `/process/gemma_3n/<session_id>`

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | string | Yes | Task to perform: `transcribe` or `analyze` |
| `model_variant` | string | No | Model to use (default: `gemma-2-9b-it`) |
| `temperature` | float | No | Generation temperature (0.1-2.0, default: 0.7) |
| `top_p` | float | No | Top-p sampling value (0.0-1.0, default: 0.9) |
| `do_sample` | boolean | No | Use sampling vs greedy (default: true) |

#### Response

```json
{
  "model": "gemma-2-9b-it",
  "task": "transcribe",
  "filename": "audio.mp3",
  "duration_seconds": 45.2,
  "sample_rate": 44100,
  "audio_features": {
    "duration_seconds": 45.2,
    "sample_rate": 44100,
    "rms_energy": 0.125,
    "spectral_centroid_hz": 2450.3,
    "zero_crossing_rate": 0.045,
    "chroma_distribution": [0.12, 0.08, ...]
  },
  "analysis_summary": "Detailed audio analysis...",
  "output_text_file": "analysis_gemma-2-9b-it_transcribe.txt",
  "output_json_file": "analysis_gemma-2-9b-it_transcribe.json"
}
```

## Model Variants

### Gemma-2-2B-IT (Instruction Tuned)
- **Size**: ~9GB
- **Speed**: ⭐⭐⭐⭐⭐ Fastest
- **Quality**: ⭐⭐⭐ Good
- **Use Case**: Quick transcription, resource-constrained
- **VRAM**: 6-8GB
- **Features Extracted**: Basic audio characteristics

### Gemma-2-9B-IT ⭐ Recommended
- **Size**: ~18GB
- **Speed**: ⭐⭐⭐⭐ Fast
- **Quality**: ⭐⭐⭐⭐ Excellent
- **Use Case**: Balanced performance and quality
- **VRAM**: 16-24GB
- **Features Extracted**: Comprehensive audio analysis

### Gemma-2-27B-IT
- **Size**: ~40GB
- **Speed**: ⭐⭐ Slower
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Use Case**: High-quality transcription and analysis
- **VRAM**: 40-80GB
- **Features Extracted**: Detailed multi-level analysis

## Audio Features Extracted

### Time-Domain Features
- **Duration**: Total audio length in seconds
- **Sample Rate**: Sampling frequency in Hz
- **RMS Energy**: Root mean square of signal amplitude

### Frequency-Domain Features
- **Spectral Centroid**: Center of mass of spectrum (Hz)
- **Zero Crossing Rate**: Number of times signal crosses zero

### Harmonic Features
- **Chroma Distribution**: 12-dimensional chromatic scale representation
- **MFCC**: Mel-Frequency Cepstral Coefficients (13 coefficients)

## Usage Examples

### Example 1: Basic Transcription
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"task": "transcribe"}' \
  "http://localhost:5000/process/gemma_3n/transcribe_001"
```

### Example 2: Detailed Audio Analysis
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "task": "analyze",
    "model_variant": "gemma-2-27b-it",
    "temperature": 0.5
  }' \
  "http://localhost:5000/process/gemma_3n/analysis_001"
```

### Example 3: Fast Transcription with 2B Model
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "task": "transcribe",
    "model_variant": "gemma-2-2b-it",
    "temperature": 0.3,
    "top_p": 0.8
  }' \
  "http://localhost:5000/process/gemma_3n/quick_001"
```

### Example 4: Creative Audio Description
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "task": "analyze",
    "temperature": 0.9,
    "top_p": 0.95
  }' \
  "http://localhost:5000/process/gemma_3n/creative_001"
```

## Generation Parameters Guide

### Temperature
Controls randomness and creativity:
- **0.1-0.3**: Deterministic, factual transcriptions
- **0.5-0.7**: Balanced (default: 0.7)
- **0.9-1.5**: Creative, descriptive analysis
- **1.5+**: Very creative (may lose accuracy)

### Top-P (Nucleus Sampling)
Controls output diversity:
- **0.5**: Conservative, focused output
- **0.8**: Balanced
- **0.9**: Recommended (default)
- **0.95+**: High diversity

## Output Format

### Text Output File
```
=== GEMMA 3N AUDIO ANALYSIS ===

Model: gemma-2-9b-it
Task: transcribe
File: song.mp3

=== AUDIO FEATURES ===

Duration: 180.45 seconds
Sample Rate: 44100 Hz
RMS Energy: 0.125
Spectral Centroid: 2450.32 Hz
Zero Crossing Rate: 0.045

=== ANALYSIS ===

[AI-generated analysis text...]
```

### JSON Output File
```json
{
  "model": "gemma-2-9b-it",
  "task": "transcribe",
  "filename": "song.mp3",
  "audio_features": {
    "duration_seconds": 180.45,
    "sample_rate": 44100,
    "rms_energy": 0.125,
    "spectral_centroid_hz": 2450.32,
    "zero_crossing_rate": 0.045,
    "chroma_distribution": [...]
  },
  "analysis": "...",
  "generation_params": {...}
}
```

## Testing

Run the Gemma 3N test suite:

```bash
python test_gemma_3n.py
```

## Performance Tips

1. **First-time setup**: Models cache locally after download
2. **Batch processing**: Process multiple files efficiently
3. **Model selection**: Choose appropriate size for hardware
4. **Temperature tuning**: Adjust for transcription vs analysis
5. **GPU optimization**: Ensure CUDA is configured

## Troubleshooting

### Out of Memory Error
```python
# Use smaller model
"model_variant": "gemma-2-2b-it"

# Or reduce generation length in models.py
max_length=1024  # Instead of 2048
```

### Slow Generation
- Use faster model variant (2B or 9B)
- Reduce max_length parameter
- Enable GPU acceleration
- Use smaller audio files for testing

### Model Download Issues
```bash
# Ensure sufficient disk space
df -h

# Set cache directory
export HF_HOME=/path/to/larger/disk
```

## Advanced Usage

### Batch Processing
```python
import requests

audio_files = ['song1.mp3', 'song2.mp3', 'song3.mp3']

for filename in audio_files:
    response = requests.post(
        'http://localhost:5000/process/gemma_3n/batch_01',
        json={'task': 'analyze'}
    )
    print(f"Processed: {filename}")
```

### Custom Configuration
Edit `config.py`:
```python
'gemma_3n': {
    'default_model': 'gemma-2-9b-it',
    'available_models': [
        'gemma-2-2b-it', 'gemma-2-9b-it', 'gemma-2-27b-it'
    ],
    'purpose': 'audio_transcription_analysis',
    'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'}
}
```

## Capabilities Summary

✅ **Supported Audio Formats**
- MP3, WAV, FLAC, M4A, OGG

✅ **Tasks**
- Transcription with feature extraction
- Detailed audio analysis
- Harmonic and spectral analysis

✅ **Features**
- GPU acceleration
- Batch processing
- Multiple model sizes
- Customizable parameters

## Limitations

- **Context window**: Processes one audio file at a time
- **Memory intensive**: Requires 6-80GB VRAM depending on model
- **Processing time**: Slower on CPU
- **Audio length**: Works best with audio up to several minutes

## Resources

- [Gemma GitHub](https://github.com/google/gemma)
- [Hugging Face Gemma Models](https://huggingface.co/collections/google/gemma-release-65d5efbf61b1d5b60efb8ac7)
- [Transformers Docs](https://huggingface.co/docs/transformers/)
- [Librosa Documentation](https://librosa.org/)

---

**Gemma 3N Audio Transcription & Analysis Ready! 🎯**
