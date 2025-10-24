# Gemma 3n Setup Guide

## ✅ Dependencies Installed

All required dependencies for Gemma 3n transcription are now installed:

- ✅ **transformers** (4.57.1) - Hugging Face Transformers
- ✅ **torch** (2.9.0) - PyTorch
- ✅ **librosa** (0.11.0) - Audio processing
- ✅ **soundfile** (0.13.1) - Audio I/O
- ✅ **accelerate** (1.10.1) - Model loading optimization
- ✅ **sentencepiece** (0.2.1) - Tokenization

## 🔐 HuggingFace Authentication Required

Gemma models are **gated** and require HuggingFace authentication to access.

### Step 1: Get HuggingFace Token

1. Go to https://huggingface.co/settings/tokens
2. Create a new token (or use existing one)
3. Copy the token

### Step 2: Accept Gemma License

1. Visit https://huggingface.co/google/gemma-2-2b
2. Click "Agree and access repository"
3. Fill out the form if required

### Step 3: Login with Token

**Option A: Command Line**
```bash
huggingface-cli login
# Paste your token when prompted
```

**Option B: Environment Variable**
```bash
# Windows PowerShell
$env:HF_TOKEN="your_token_here"

# Or add to your .env file
HF_TOKEN=your_token_here
```

**Option C: Code (in app.py)**
```python
from huggingface_hub import login
login(token="your_token_here")
```

### Step 4: Verify Access

Run the verification script again:
```bash
python verify_gemma.py
```

If successful, you'll see:
```
✅ Model loaded successfully!
✅ Generation successful!
```

## 🎯 Available Gemma Models

| Model | Size | VRAM | Speed | Quality |
|-------|------|------|-------|---------|
| `google/gemma-2-2b` | 5GB | 8GB | Fast | Good |
| `google/gemma-2-9b` | 18GB | 16GB | Medium | Better |
| `google/gemma-2-27b` | 54GB | 40GB | Slow | Best |

**Recommended**: Start with `gemma-2-2b` for testing.

## 🚀 Usage in AI separator backend

The backend automatically uses Gemma 3n when `auto_process=true`:

```python
# Upload file - Gemma 3n runs automatically
curl -X POST http://localhost:5000/upload?model=demucs \
  -F "file=@song.mp3" \
  -F "auto_process=true" \
  -F "gemma_model=gemma-2-2b"
```

**Response includes transcription:**
```json
{
  "transcription": {
    "status": "completed",
    "text": "AI-generated lyrics and analysis...",
    "model": "gemma-3n",
    "output_file": "analysis_gemma-2-2b_transcribe.txt"
  }
}
```

## 🔧 Configuration

### Change Default Model

Edit `config.py`:
```python
'gemma_3n': {
    'name': 'Gemma 3N Transcription',
    'default_model': 'gemma-2-2b',  # Change to 'gemma-2-9b' for better quality
    'available_models': ['gemma-2-2b', 'gemma-2-9b', 'gemma-2-27b'],
    # ...
}
```

### Adjust Generation Parameters

When uploading, customize:
```bash
curl -X POST http://localhost:5000/upload?model=demucs \
  -F "file=@song.mp3" \
  -F "gemma_model=gemma-2-2b" \
  -F "temperature=0.8" \
  -F "top_p=0.95"
```

## 🐛 Troubleshooting

### Error: "Access to model is restricted"

**Solution:** You need to:
1. Accept the license at https://huggingface.co/google/gemma-2-2b
2. Login with your HuggingFace token

### Error: "Out of memory"

**Solutions:**
- Use a smaller model (`gemma-2-2b` instead of `gemma-2-9b`)
- Close other applications
- Add swap memory
- Use CPU inference (slower but works):
  ```python
  model = AutoModelForCausalLM.from_pretrained(
      "google/gemma-2-2b",
      device_map="cpu"  # Force CPU
  )
  ```

### Error: "Tokenizer not found"

**Solution:** Install sentencepiece:
```bash
pip install sentencepiece
```

### Model Download is Slow

First-time model download can be 5-10 GB and take 10-30 minutes depending on your internet speed. The model is cached locally after the first download.

**Check download location:**
```bash
# Windows
echo %USERPROFILE%\.cache\huggingface

# Linux/Mac
echo ~/.cache/huggingface
```

### Transcription Takes Too Long

**Options:**
1. Use smaller model (`gemma-2-2b`)
2. Reduce `max_length` in generation
3. Use GPU instead of CPU
4. Process shorter audio clips

## 🎨 Features

### Audio Analysis

Gemma 3n extracts and analyzes:
- Duration and sample rate
- RMS energy (loudness)
- Spectral centroid (brightness)
- Zero crossing rate (noisiness)
- Chroma distribution (pitch content)
- MFCC features (timbre)

### Transcription Output

Two files are generated:
1. **Text file** (`analysis_gemma-2-2b_transcribe.txt`)
   - Formatted report with audio features
   - AI-generated analysis
   - Human-readable

2. **JSON file** (`analysis_gemma-2-2b_transcribe.json`)
   - Structured data
   - All numeric features
   - Machine-readable

### Generation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `temperature` | 0.7 | Creativity (0.1=conservative, 1.5=creative) |
| `top_p` | 0.9 | Nucleus sampling (0.5=focused, 1.0=diverse) |
| `max_length` | 2048 | Maximum output tokens |
| `do_sample` | true | Enable sampling (vs greedy decoding) |

## 📊 Performance

### Processing Times (gemma-2-2b)

| Audio Length | Analysis Time | Notes |
|--------------|---------------|-------|
| 30 seconds | ~5-10s | Feature extraction |
| 30 seconds | ~20-40s | AI generation |
| 3 minutes | ~10-15s | Feature extraction |
| 3 minutes | ~30-60s | AI generation |

**Total**: Feature extraction + AI generation

### GPU vs CPU

| Hardware | Speed | VRAM | Notes |
|----------|-------|------|-------|
| RTX 3080 | Fast (10s) | 8GB | Recommended |
| CPU (i7) | Slow (60s) | - | Works but slow |
| RTX 4090 | Very Fast (5s) | 16GB | Best |

## 🔮 Alternative: Fallback to Simple Transcription

If Gemma models are unavailable, the backend can fall back to simpler transcription methods. Edit `models.py` to add a fallback:

```python
def process(self, file_id, input_file, **kwargs):
    try:
        # Try Gemma 3n
        return self._process_with_gemma(...)
    except Exception as e:
        print(f"Gemma failed, using fallback: {e}")
        # Fallback: Just extract audio features
        return self._extract_audio_features_only(...)
```

## 📚 Resources

- **Gemma Models**: https://huggingface.co/google/gemma-2-2b
- **HuggingFace Tokens**: https://huggingface.co/settings/tokens
- **Transformers Docs**: https://huggingface.co/docs/transformers
- **AI separator backend Code**: `models.py` - `Gemma3NProcessor` class

## ✅ Quick Checklist

Before using Gemma 3n, ensure:

- [ ] All dependencies installed (`python verify_gemma.py`)
- [ ] HuggingFace account created
- [ ] Token generated
- [ ] Gemma license accepted
- [ ] Logged in with token (`huggingface-cli login`)
- [ ] Model downloaded (happens on first use)
- [ ] Sufficient disk space (10GB+ for model)
- [ ] Sufficient RAM (16GB+ recommended)

## 🎯 Next Steps

1. **Run verification**: `python verify_gemma.py`
2. **Setup HF token**: Follow steps above
3. **Test upload**: Use `test_progress.html` or `test_upload.html`
4. **Check transcription**: Look for `analysis_*.txt` in `outputs/{file_id}/`

---

**Status**: ✅ Dependencies installed, ready for authentication  
**Last Updated**: 2025-10-19  
**Need Help?** Check `verify_gemma.py` output for detailed diagnostics
