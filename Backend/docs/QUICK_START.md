# AI Music Separator - Quick Start Guide

## ✅ Setup Complete!

Your AI Music Separator backend is now fully configured with:
- ✅ Real-time WebSocket progress tracking
- ✅ Gemma 3n AI transcription (10 GB model downloaded)
- ✅ Beautiful animated progress UI
- ✅ Karaoke generation with synced lyrics

---

## 🚀 Starting the Server

### Option 1: PowerShell Script (Recommended)
```powershell
.\start_app.ps1
```
**Benefits:**
- Automatically uses correct virtual environment
- Verifies dependencies before starting
- Shows clear startup information
- Checks for missing packages

### Option 2: Direct Python (Advanced)
```powershell
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\Scripts\python.exe app.py
```

### Option 3: Activate venv first
```powershell
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\Scripts\Activate.ps1
python app.py
```

---

## 🌐 Accessing the Server

Once started, the server is available at:
- **Local:** http://localhost:5000
- **Network:** http://192.168.0.13:5000

### Test UI (Progress Tracking Demo):
- http://localhost:5000/test_progress.html

### API Endpoints:
- `POST /upload` - Upload audio file with auto-processing
- `POST /separate` - Separate vocals/instrumentals
- `POST /transcribe` - Transcribe audio with Gemma 3n
- `POST /generate_karaoke` - Generate karaoke files
- `GET /health` - Server health check

---

## 📁 Project Structure

```
AiMusicSeparator-AI separator backend/
├── api/.venv/              # Virtual environment (Python 3.13.5)
├── app.py                  # Main Flask application
├── models.py               # Gemma3NProcessor for AI transcription
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
├── start_app.ps1          # Startup script (use this!)
├── setup_hf_token.py      # HuggingFace authentication
├── verify_gemma.py        # Dependency verification
├── test_progress.html     # Beautiful progress demo UI
├── uploads/               # Uploaded audio files
├── outputs/               # Processing results
│   └── <uuid>/           # Per-file outputs
│       ├── vocals.wav
│       ├── instrumentals.wav
│       ├── transcription_base.txt
│       ├── transcription_base.json
│       └── karaoke/      # Karaoke files
│           ├── song.lrc  # Synced lyrics
│           └── song.mp3  # Audio with embedded lyrics
└── server/               # Server modules
```

---

## 🎵 How to Use

### 1. Upload Audio File (Drag & Drop)
Visit http://localhost:5000/test_progress.html and drag an audio file onto the upload area.

### 2. Watch Real-Time Progress
The UI shows animated progress bars for each stage:
- 📤 **Upload** - File upload progress
- 🎤 **Separation** - Vocal/instrumental separation
- 📝 **Transcription** - AI analysis with Gemma 3n
- 🎤 **Karaoke** - Synced lyrics generation
- ✅ **Complete** - Download ready

### 3. Download Results
Once complete, download links appear for:
- Vocals (separated vocal track)
- Instrumentals (separated instrumental track)
- Transcription (AI-generated lyrics/analysis)
- Karaoke files (LRC + audio with embedded lyrics)

---

## 🔧 Common Commands

### Verify Gemma Setup
```powershell
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\Scripts\python.exe verify_gemma.py
```

### Check Python Environment
```powershell
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\Scripts\python.exe --version
```

### Install Missing Dependencies
```powershell
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\Scripts\python.exe -m pip install transformers accelerate sentencepiece Flask-SocketIO
```

### Update Requirements
```powershell
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 📦 Installed Dependencies

### Core Framework:
- Flask 2.3.3 - Web framework
- Flask-CORS 4.0.0 - Cross-origin support
- Flask-SocketIO - WebSocket support

### AI & ML:
- transformers 4.57.1 - HuggingFace models
- torch 2.9.0+cpu - PyTorch framework
- accelerate 1.10.1 - Model optimization
- sentencepiece 0.2.1 - Tokenization
- openai-whisper - Speech recognition

### Audio Processing:
- demucs - Audio source separation
- librosa 0.11.0 - Audio analysis
- soundfile 0.13.1 - Audio I/O
- pydub - Audio manipulation
- audiocraft - Music generation

### Utilities:
- mutagen - Audio metadata
- numpy - Numerical computing
- scipy - Scientific computing
- pandas - Data manipulation

---

## 🐛 Troubleshooting

### Error: "No module named 'transformers'"
**Solution:** Use `.\start_app.ps1` instead of `python app.py`
- The script ensures the correct virtual environment is used

### Server Won't Start
**Check:**
1. Virtual environment activated: `.\start_app.ps1`
2. Dependencies installed: Run verify_gemma.py
3. Port 5000 not in use: `netstat -ano | findstr :5000`

### Gemma Model Not Loading
**Solutions:**
1. Check HuggingFace authentication: `python setup_hf_token.py`
2. Accept license: https://huggingface.co/google/gemma-2-2b
3. Verify dependencies: `python verify_gemma.py`

### First Transcription Slow
**Expected behavior:** First use downloads ~10 GB model (10-30 minutes)
- Subsequent uses are instant (model cached locally)

---

## 📊 Performance Notes

### Gemma 3n Model:
- **Size:** ~10 GB
- **First download:** 10-30 minutes
- **Memory:** 8-16 GB RAM recommended
- **Device:** CPU (bfloat16 precision)
- **Inference time:** 30-60 seconds per audio file

### Audio Separation (Demucs):
- **Time:** 1-5 minutes per song
- **Quality:** High-quality vocal/instrumental separation
- **Format:** WAV output (uncompressed)

### Karaoke Generation:
- **Time:** 5-10 seconds
- **Output:** LRC file + MP3 with ID3 lyrics tag
- **Sync:** Time-aligned lyrics with music

---

## 🎯 Next Steps

1. **Test the full pipeline:**
   - Upload an audio file via test_progress.html
   - Watch real-time progress updates
   - Download karaoke files

2. **Integrate with frontend:**
   - Use WebSocket events for live progress
   - Connect to http://192.168.0.13:5000 from other devices

3. **Optimize performance:**
   - Consider GPU support for faster inference
   - Tune Gemma model parameters in models.py

4. **Deploy to production:**
   - Use `gunicorn` or `waitress` for production server
   - Set up reverse proxy (nginx)
   - Configure environment variables

---

## 📚 Documentation

- **GEMMA_SETUP_GUIDE.md** - Comprehensive Gemma 3n setup
- **GEMMA_DEPENDENCIES.md** - Quick dependency reference
- **/part of AI separator backend/README.md** - Progress tracking details
- **server/CHANGELOG.md** - Change history

---

## 🆘 Getting Help

If you encounter issues:
1. Check logs in terminal output
2. Run verification: `python verify_gemma.py`
3. Review documentation files
4. Check GitHub issues: Almir-ctrl/AiMusicSeparator-AI separator backend

---

**Last Updated:** October 19, 2025  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
