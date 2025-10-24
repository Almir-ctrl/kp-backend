<!-- Pointer: moved to /part of Backend/gemma3n/GEMMA_SETUP_GUIDE.md -->

See canonical copy at: `/part of AI separator backend/gemma3n/GEMMA_SETUP_GUIDE.md`
> This quick start has moved to the part of Backend area.

Canonical location:

- /part of AI separator backend/gemma3n/GEMMA_SETUP_GUIDE.md

If your scripts depend on this exact path, please update them to the new path or open an issue for a compatibility redirect.
# Gemma 3N Setup Guide - Quick Start

## One-Time Setup (5 minutes)

### 1. Install Python Dependencies
```bash
cd server
pip install -r requirements.txt
```

This installs:
- `transformers` - Gemma 3N model loader
- `torch` - Deep learning framework
- `librosa` - Audio processing
- `whisper` - Speech transcription

### 2. Verify Installation
```bash
# Test Python packages
python -c "import torch, transformers, librosa, whisper; print('✓ All packages installed')"
```

### 3. Download Models (First Run Only)
Models download automatically on first use (~9GB total):
- Gemma 2 9B (~5GB)
- Whisper base model (~140MB)

**Storage required:** 15GB free space

---

## Running the Application

### Terminal 1: Start Flask Backend
```bash
cd server
python main.py
```

**Expected output:**
```
✓ Demucs model loaded
✓ Whisper model loaded
✓ Flask server running on http://localhost:5000
```

### Terminal 2: Start React Lion's Roar Studio
```bash
npm run dev
```

**Expected output:**
```
✓ VITE v6.4.0 ready in 190 ms
✓ Local: http://localhost:3000/
```

### Browser: Open http://localhost:3000

---

## Testing Gemma 3N Integration

### Test 1: Vocal Coaching
1. Upload or select a song
2. Record a performance (or use existing)
3. Click **"Get AI Feedback"** button in Vocal Coach window
4. Wait 5-15 seconds
5. ✅ Should see coaching feedback from Gemma 3N

### Test 2: Key Detection
1. Select a song
2. Click **"Detect Key"** button in Scoreboard window
3. Wait for upload and processing (~10-30 sec)
4. ✅ Should see detected key (e.g., "C Major")

### Test 3: Check Backend Health
```bash
curl http://localhost:5000/health
# Response: {"status": "ok", "models": {...}}
```

---

## Troubleshooting

### Problem: "Module not found: transformers"
```bash
# Solution: Install missing package
pip install transformers torch
```

### Problem: "CUDA out of memory"
```bash
# Solution: Use CPU instead
# Edit server/main.py line 695:
# Change: device_map='auto'
# To: device_map='cpu'
```

### Problem: Lion's Roar Studio can't connect to backend
```bash
# Check backend is running:
curl http://localhost:5000/health

# If not running, start it:
cd server && python main.py
```

### Problem: Models not downloading
```bash
# Check disk space:
# Models cache: ~/.cache/huggingface/
# Need: 15GB free

# Force re-download:
rm -rf ~/.cache/huggingface/hub
# Then restart and let models download again
```

---

## Configuration

### Switch Model Variant
Edit requests to use different Gemma variants:

**In VocalCoachWindow.tsx:**
```typescript
// Current: Small model (fast)
model_variant: 'gemma-2-9b-it'

// Alternative: Large model (slower, better quality)
model_variant: 'gemma-2-27b-it'
```

### Adjust Processing Timeout
**In ScoreboardWindow.tsx:**
```typescript
// Current: 30 attempts (30 seconds max)
while (result.status === 'processing' && attempts < 30)

// For slower systems:
while (result.status === 'processing' && attempts < 60)  // 60 seconds
```

---

## Performance Tips

### For Faster Processing
1. Use GPU: Ensure CUDA is installed
2. Use smaller model: `gemma-2-9b-it` (default)
3. Close other applications
4. Use SSD for faster model caching

### For Lower Memory Usage
1. Use CPU mode (slower but uses less VRAM)
2. Use smaller model
3. Restart Flask between heavy tasks

---

## File Structure

```
project/
├── server/
│   ├── main.py                 # Flask backend with Gemma 3N
│   ├── requirements.txt        # Python dependencies
│   └── GEMMA3_SETUP.md        # AI separator backend setup docs
│
├── components/windows/
│   ├── VocalCoachWindow.tsx   # ✓ Uses Gemma 3N backend
│   └── ScoreboardWindow.tsx   # ✓ Uses Gemma 3N backend
│
├── context/
│   └── AppContext.tsx         # ✓ Removed Google API import
│
└── GEMMA3N_MIGRATION.md       # Full migration guide
```

---

## Next Steps

After setup, you can:

1. **Customize Prompts:** Edit prompt strings in component files
2. **Add New Tasks:** Extend `process_with_gemma_3n()` in server/main.py
3. **Optimize Performance:** Adjust model variants and timeouts
4. **Monitor Processing:** Check server logs for model inference times

---

## Environment Variables (No Longer Needed!)

❌ **REMOVED:** GEMINI_API_KEY
- Previously required for Google API
- Now completely optional
- Can delete from .env file

---

## Support

For issues or questions:
1. Check backend logs: `python main.py` output
2. Check frontend console: Browser DevTools → Console
3. Check API response: Network tab in DevTools
4. Review `server/main.py` lines 670-800 for implementation

---

**Ready to go!** 🚀 Start with Terminal 1 backend, then Terminal 2 frontend.
