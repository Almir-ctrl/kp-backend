# ⚠️ IMPORTANT: How to Start the Server

**Always use the startup script! Never run `python app.py` directly!**

---

## ✅ CORRECT Way to Start Server:

```powershell
.\start_app.ps1
```

**This script:**
- ✅ Uses the virtual environment Python
- ✅ Verifies all dependencies are installed
- ✅ Shows clear startup information
- ✅ Ensures Demucs and Gemma work correctly

---

## ❌ WRONG Way (Don't Do This):

```powershell
python app.py
```

**Problems:**
- ❌ Uses system Python (not virtual environment)
- ❌ Can't find transformers, demucs, or other packages
- ❌ Gemma transcription fails with "No module named 'transformers'"
- ❌ Demucs separation may fail
- ❌ Auto-processing doesn't work

---

## Why This Matters

### Virtual Environment Path:
```
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\
```

All packages are installed here:
- transformers 4.57.1
- torch 2.9.0+cpu
- demucs
- librosa 0.11.0
- soundfile 0.13.1
- accelerate 1.10.1
- sentencepiece 0.2.1
- Flask-SocketIO
- And 15+ more packages

### When you run `python app.py`:
- Uses: `C:\Python313\python.exe` (system Python)
- Looks in: System site-packages
- Result: ❌ "No module named 'transformers'"

### When you run `.\start_app.ps1`:
- Uses: `api\.venv\Scripts\python.exe` (virtual environment)
- Looks in: `api\.venv\Lib\site-packages`
- Result: ✅ All imports work perfectly

---

## Quick Reference

### Start Server:
```powershell
.\start_app.ps1
```

### Stop Server:
```powershell
# Press Ctrl+C in the terminal
# Or:
taskkill /F /IM python.exe
```

### Restart Server:
```powershell
# Ctrl+C to stop, then:
.\start_app.ps1
```

### Check Server Status:
- Open: http://localhost:5000/test_progress.html
- Should show: ✅ Connected to server (green)

### Test Imports:
```powershell
python test_imports.py
```

---

## Troubleshooting

### Error: "No module named 'transformers'" or "No module named 'demucs'"
**Solution:** Stop the server and restart with `.\start_app.ps1`

Never use `python app.py` directly!

### Error: "port 5000 already in use"
**Solution:** 
```powershell
taskkill /F /IM python.exe
.\start_app.ps1
```

### Server won't start
**Check:**
1. Are you in the correct directory? `C:\Users\almir\AiMusicSeparator-AI separator backend`
2. Does the venv exist? `Test-Path api\.venv\Scripts\python.exe`
3. Run: `.\start_app.ps1` (not `python app.py`)

---

## What start_app.ps1 Does

### 1. Checks Virtual Environment
```powershell
if (-not (Test-Path $PYTHON_EXE)) {
    # Creates venv if missing
    python -m venv $VENV_PATH
}
```

### 2. Verifies Dependencies
```powershell
$CHECK_DEPS = & $PYTHON_EXE -c "import transformers, torch, ..."
if ($CHECK_DEPS -notmatch "OK") {
    # Installs missing packages
}
```

### 3. Shows Environment Info
```
Environment Information:
  Python: C:\...\api\.venv\Scripts\python.exe
  Version: Python 3.13.5
  App: app.py
```

### 4. Starts Server with Correct Python
```powershell
& $PYTHON_EXE app.py
```

---

## Alternative Methods (Advanced)

### Method 1: Activate venv first (if you prefer)
```powershell
api\.venv\Scripts\Activate.ps1
python app.py
```

### Method 2: Use full Python path
```powershell
C:\Users\almir\AiMusicSeparator-AI separator backend\api\.venv\Scripts\python.exe app.py
```

### Method 3: Use the startup script (recommended)
```powershell
.\start_app.ps1
```

**Recommendation:** Always use Method 3 (start_app.ps1) for consistency!

---

## Remember

1. ✅ **DO:** Use `.\start_app.ps1`
2. ❌ **DON'T:** Use `python app.py`

3. ✅ **DO:** Check connection status in UI (should be green)
4. ❌ **DON'T:** Ignore import errors in logs

5. ✅ **DO:** Verify dependencies with `python test_imports.py`
6. ❌ **DON'T:** Assume system Python has all packages

---

## Server URLs

Once started, access at:
- **Local:** http://localhost:5000
- **Network:** http://192.168.0.13:5000
- **Test UI:** http://localhost:5000/test_progress.html

---

## Summary

**Rule #1:** Always start the server with `.\start_app.ps1`

**Why:** Ensures virtual environment is used, all dependencies available, and everything works correctly.

**Never forget:** `python app.py` = ❌ Wrong! ❌ No packages! ❌ Errors!

**Always remember:** `.\start_app.ps1` = ✅ Correct! ✅ All packages! ✅ Works!

---

**Last Updated:** October 19, 2025  
**Status:** Server running correctly with virtual environment  
**Next Action:** Upload audio to http://localhost:5000/test_progress.html
