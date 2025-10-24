# 🧪 QUICK TEST GUIDE

**AI separator backend Status:** ✅ Running on http://127.0.0.1:5000  
**Changes Applied:** DELETE endpoint + Whisper integration

---

## ⚡ Quick Tests (5 minutes)

### Test 1: DELETE Endpoint (30 seconds)
```powershell
# Option A: curl test
curl -X DELETE http://127.0.0.1:5000/songs/test-id -v

# Expected: 404 (file not found) BUT with CORS headers
# Should see: Access-Control-Allow-Origin: *
# Should NOT see: CORS Preflight Did Not Succeed

# Option B: Lion's Roar Studio test
# 1. Hard refresh browser: Ctrl + Shift + R
# 2. Go to Library
# 3. Click Delete on any song
# 4. Open Console (F12)
# 5. Should see: Successfully deleted song on server
# 6. Should NOT see: CORS error or NetworkError
```

---

### Test 2: Whisper Transcription (2-3 minutes)
```powershell
# Upload NEW song (old songs still use Gemma 3N)
# 1. Go to SongEditor in frontend
# 2. Upload audio file (MP3/WAV)
# 3. Enter artist/song name
# 4. Click Upload
# 5. Wait for processing (watch backend terminal)
# 6. Look for: "Whisper transcription completed successfully"
# 7. Look for: "Gemma 3N analysis completed successfully" (optional)
# 8. Look for: "Karaoke generation completed"
```

---

### Test 3: Lyrics Display (1 minute)
```powershell
# After upload completes:
# 1. Select uploaded song in Library
# 2. Click on song to play
# 3. Open LyricsWindow
# 4. Should see: ACTUAL song lyrics
# 5. Should NOT see: "Select a song to view lyrics"
# 6. Should NOT see: Audio analysis text like "Duration: 180s, RMS: 0.045..."
```

---

### Test 4: External Player (1 minute)
```powershell
# With song playing:
# 1. Click "External Player" button
# 2. External window opens
# 3. Should show: Synced lyrics
# 4. Should NOT show: "No song playing, waiting for lyrics data"
# 5. Lyrics should sync with audio playback
```

---

### Test 5: Karaoke Files (30 seconds)
```powershell
# Check generated karaoke files
$fileId = "your-new-song-file-id"  # Get from upload response or Console
Get-Content "C:\Users\almir\AiMusicSeparator-AI separator backend\outputs\Karaoke-pjesme\$fileId\${fileId}_karaoke.lrc"

# ✅ SHOULD SEE (CORRECT):
# [ti:Song Title]
# [ar:Artist Name]
# [00:00.00]Never gonna give you up
# [00:03.20]Never gonna let you down
# [00:06.40]Never gonna run around and desert you

# ❌ SHOULD NOT SEE (WRONG - old Gemma 3N):
# [00:00.00]This audio has a duration of 180 seconds
# [00:30.00]RMS energy averaging 0.045 indicates moderate volume
# [01:00.00]Spectral centroid at 2500 Hz suggests bright timbre
```

---

## 🔍 Debugging

### If DELETE Fails
```javascript
// Open browser Console (F12)
// Try manual DELETE:
fetch('http://127.0.0.1:5000/songs/test-id', { method: 'DELETE' })
  .then(r => {
    console.log('Status:', r.status);  // Should be 404 (not found) or 200 (deleted)
    console.log('CORS:', r.headers.get('Access-Control-Allow-Origin'));  // Should be '*'
    return r.json();
  })
  .then(data => console.log('Response:', data))
  .catch(err => console.error('Error:', err));

// If still CORS error: AI separator backend might not have restarted properly
// Solution: Stop-Process -Name "python" -Force; python app.py
```

---

### If Lyrics Still Wrong
```javascript
// Open Console (F12) after selecting song
console.log(currentSong?.timedLyrics);
// Should be array of objects: [{ timestamp: 0, text: "lyrics..." }, ...]

// If undefined or empty:
console.log(currentSong?.url);
// Get file_id from URL

// Check backend files:
// C:\Users\almir\AiMusicSeparator-AI separator backend\outputs\{file_id}\transcription_base.txt
// Should contain actual lyrics, not audio analysis

// If still audio analysis:
// - Song was uploaded BEFORE Whisper integration
// - Solution: Delete and re-upload song
```

---

### Check AI separator backend Logs
```powershell
# AI separator backend terminal should show:
# "Auto-transcribing {file_id} with Whisper"  ← NEW
# "Whisper transcription completed successfully"  ← NEW
# "Analyzing audio with Gemma 3N"  ← NEW (optional)
# "Gemma 3N analysis completed successfully"  ← NEW (optional)
# "Auto-generating karaoke for {file_id}"
# "Karaoke generation completed"

# If you see:
# "Auto-transcribing {file_id} with Gemma 3n"  ← OLD, means backend didn't restart!
# Solution: Stop-Process -Name "python" -Force; python app.py
```

---

## 📊 Expected Results

### AI separator backend Response (Upload)
```json
{
  "file_id": "uuid-here",
  "transcription": {
    "status": "completed",
    "text": "Never gonna give you up\nNever gonna let you down...",
    "model": "whisper",  // ← NEW (was "gemma-3n")
    "model_variant": "base"
  },
  "audio_analysis": {  // ← NEW field (separate from transcription)
    "status": "completed",
    "analysis": "This audio features consistent rhythm...",
    "model": "gemma-3n"
  },
  "karaoke": {
    "status": "completed",
    "lrc_file": "uuid_karaoke.lrc",
    "audio_with_metadata": "uuid_karaoke.mp3"
  }
}
```

---

## 🎯 Success Criteria

| Test | Pass Criteria |
|------|---------------|
| **DELETE Endpoint** | No CORS errors, song removed from backend |
| **Whisper Transcription** | AI separator backend logs show "Whisper transcription completed" |
| **Lyrics Display** | LyricsWindow shows actual song lyrics |
| **External Player** | Shows synced lyrics, not "waiting for data" |
| **Karaoke Files** | LRC contains lyrics, not audio analysis |

---

## ⚠️ Common Issues

### Issue 1: Still Seeing Gemma 3N as Transcription
**Symptom:** AI separator backend logs show "Auto-transcribing with Gemma 3n"  
**Cause:** AI separator backend didn't restart with new code  
**Solution:**
```powershell
Stop-Process -Name "python" -Force
cd C:\Users\almir\AiMusicSeparator-AI separator backend
python app.py
# Wait for: "Running on http://127.0.0.1:5000"
```

---

### Issue 2: Old Songs Still Show Analysis Text
**Symptom:** LyricsWindow shows "Duration: 180s, RMS: 0.045..."  
**Cause:** Song was uploaded before Whisper integration  
**Solution:**
- Delete old song (now works with DELETE endpoint!)
- Re-upload song
- New upload will use Whisper workflow

---

### Issue 3: Lion's Roar Studio Not Updating
**Symptom:** Changes not visible in browser  
**Cause:** Cached frontend or API responses  
**Solution:**
```powershell
# Hard refresh
# Ctrl + Shift + R in browser

# Or restart Vite dev server
cd C:\Users\almir\lion's-roar-karaoke-studio
Stop-Process -Name "node" -Force
npm run dev
```

---

## 🚀 Full Test Workflow (End-to-End)

```powershell
# 1. Verify backend running
curl http://127.0.0.1:5000/health

# 2. Hard refresh frontend
# Ctrl + Shift + R

# 3. Upload NEW song
# - Go to SongEditor
# - Upload audio
# - Enter artist/name
# - Wait for "Processing complete"

# 4. Check backend logs
# Should see:
# - "Whisper transcription completed"
# - "Gemma 3N analysis completed"
# - "Karaoke generation completed"

# 5. Select song in Library
# - Click to play
# - Open LyricsWindow
# - Verify: Shows actual lyrics

# 6. Open external player
# - Click "External Player"
# - Verify: Shows synced lyrics

# 7. Check karaoke files
$fileId = "from-upload-response"
Get-Content "outputs\Karaoke-pjesme\$fileId\${fileId}_karaoke.lrc"
# Verify: Contains actual lyrics

# 8. Test DELETE
# - Click Delete on song
# - Verify: No CORS errors
# - Verify: Song removed from backend
```

---

## 📞 If Tests Fail

**Contact Points:**
1. Check `SESSION_COMPLETE.md` for full changes
2. Check `WHISPER_KARAOKE_FIX.md` for detailed Whisper integration
3. Check `TWO_PROBLEMS_FIX.md` for original problem diagnosis
4. AI separator backend logs: Look for errors in terminal
5. Lion's Roar Studio console: Check for API errors (F12)

**Rollback (if needed):**
```powershell
# If changes cause issues, rollback:
git diff app.py  # Review changes
git checkout app.py  # Undo changes
python app.py  # Restart with old code
```

---

**Quick Test Time:** ~5 minutes total  
**Full E2E Test:** ~10 minutes  
**Last Updated:** 2025-06-14
