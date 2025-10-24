# 2025-10-21: sync_torch_cuda.ps1 pip/pip3 Compatibility

The `scripts/sync_torch_cuda.ps1` script now detects and uses either `pip` or `pip3` for all install commands. This ensures the script works on systems where only `pip3` is available, improving reproducibility and setup reliability for CUDA/PyTorch environments.

# Duplicate Detection & Smart Processing - COMPLETE ✅

## Changes Implemented

### 1. **AI separator backend - Missing Dependencies Installed** ✅
```bash
pip install transformers mutagen librosa soundfile
```
- **transformers**: Required for Gemma 3N AI model
- **mutagen**: Required for MP3 metadata (ID3 tags) in karaoke generation
- **librosa/soundfile**: Audio processing utilities

---

### 2. **AI separator backend - Duplicate Upload Prevention** ✅

**Location:** `app.py` - new helper function `check_duplicate_upload()`

**Behavior:**
- When user uploads a file, backend checks `outputs/*/metadata.json` for `original_filename`
- If match found → return **409 Conflict** with existing `file_id`
- Response:
  ```json
  {
    "error": "Song already exists",
    "file_id": "existing-uuid-here",
    "message": "This song has already been uploaded",
    "existing": true
  }
  ```

**Console Log:**
```
Duplicate upload detected: Artist - Song.mp3 (existing file_id: abc-123)
```

---

### 3. **AI separator backend - Skip Redundant Processing** ✅

**Location:** `app.py` - new helper function `check_output_exists()`

**Behavior:**
- Before processing with **Demucs** → check if `vocals.mp3` already exists
- Before processing with **Whisper** → check if `transcription_base.txt` already exists
- If output exists → return **200 OK** with existing files (no re-processing)
- Response:
  ```json
  {
    "file_id": "abc-123",
    "model": "demucs",
    "status": "completed",
    "message": "Demucs output already exists",
    "files": [...],
    "skipped": true,
    "existing_output": "vocals.mp3"
  }
  ```

**Console Log:**
```
Output already exists for demucs: C:\...\outputs\abc-123\vocals.mp3
```

---

### 4. **AI separator backend - Karaoke API Fixed** ✅

**Problem:** 
```python
TypeError: KaraokeProcessor.process() missing 2 required positional arguments: 
'vocals_path' and 'transcription_text'
```

**Solution:** When `model_name == 'karaoke'`, backend now:
1. Reads `vocals.mp3` from `outputs/{file_id}/`
2. Reads `transcription_base.txt` or `.json` from `outputs/{file_id}/`
3. Reads `metadata.json` for artist/song_name
4. Calls `KaraokeProcessor.process(file_id, input_file, vocals_path, transcription_text, ...)`

**Validation:**
- If vocals missing → return **400 Bad Request**: "Vocals not found. Please run Demucs separation first."
- If transcription missing → return **400 Bad Request**: "Transcription not found. Please run Whisper transcription first."

---

### 5. **Lion's Roar Studio - Handle 409 Duplicate Response** ✅

**Location:** `AppContext.tsx` - `processSongWithAdvancedTool()` function

**Behavior:**
- Upload returns **409** → Lion's Roar Studio shows: ⚠️ "Song already exists! Opening existing version."
- Lion's Roar Studio searches `songs` array for existing `file_id`
- If found → calls `setCurrentSong(existingSong)` and shows: ✅ "Switched to existing song: {title}"
- If not found → calls `fetchSongsFromBackend()` and retries
- **No re-processing** → exits early after switching to existing song

**User Experience:**
1. User uploads "Artist - Song.mp3" (already uploaded before)
2. Toast notification: ⚠️ "Song already exists! Opening existing version."
3. App switches to existing song in library
4. User can immediately use existing outputs (vocals, transcription, etc.)

---

## Testing Instructions

### Test 1: Duplicate Upload Detection
```bash
# 1. Upload a song via frontend (Library → Upload File)
# 2. Try uploading SAME song again
# Expected:
# - AI separator backend logs: "Duplicate upload detected: ..."
# - Lion's Roar Studio shows: "Song already exists! Opening existing version."
# - Lion's Roar Studio switches to existing song (no re-upload/re-process)
```

### Test 2: Skip Existing Demucs Output
```bash
# 1. Upload song and process with Demucs (creates vocals.mp3)
# 2. Try processing with Demucs AGAIN on same song
# Expected:
# - AI separator backend logs: "Output already exists for demucs: .../vocals.mp3"
# - Response: { "skipped": true, "existing_output": "vocals.mp3" }
# - No re-processing (instant return)
```

### Test 3: Karaoke Generation with Dependencies
```bash
# 1. Upload song
# 2. Run Demucs separation (creates vocals.mp3 + instrumental.mp3)
# 3. Run Whisper transcription (creates transcription_base.txt)
# 4. Run Karaoke generation
# Expected:
# - AI separator backend finds vocals.mp3 and transcription_base.txt automatically
# - Karaoke generates .lrc file with timestamps
# - No errors about missing mutagen/transformers
```

### Test 4: Karaoke Without Prerequisites
```bash
# 1. Upload song (no processing)
# 2. Try to run Karaoke immediately
# Expected:
# - AI separator backend returns 400 Bad Request
# - Error: "Vocals not found. Please run Demucs separation first."
```

---

## UI Enhancements TODO ⚠️

**Task 6 - Not Yet Implemented:**
> "In AdvancedToolsWindow/LionsRoarWindow, disable tool buttons if outputs already exist"

**Example:**
- If `vocals.mp3` exists → disable "Create Instrumental" button (already done)
- If `transcription_base.txt` exists → disable "Transcribe" button (already done)
- Show badge: "✅ Already created" on disabled buttons

**Implementation needed:**
```tsx
// In AdvancedToolsWindow.tsx or LionsRoarWindow.tsx
const hasVocals = currentSong?.files?.some(f => f.includes('vocals.mp3'));
const hasTranscription = currentSong?.files?.some(f => f.includes('transcription'));

<button 
  disabled={hasVocals}
  className={hasVocals ? 'opacity-50 cursor-not-allowed' : ''}
>
  {hasVocals ? '✅ Vocals Exist' : 'Create Vocals'}
</button>
```

---

## Summary of Fixed Errors

### Before:
```
❌ ModuleNotFoundError: No module named 'mutagen'
❌ TypeError: KaraokeProcessor.process() missing 2 required positional arguments
❌ No duplicate detection → users upload same song multiple times
❌ No skip logic → re-processing wastes time and resources
```

### After:
```
✅ All dependencies installed (transformers, mutagen, librosa, soundfile)
✅ Karaoke API fixed - reads vocals & transcription from outputs/{file_id}/
✅ Duplicate uploads return 409 Conflict with existing file_id
✅ Redundant processing skipped (vocals, transcription already exist)
✅ Lion's Roar Studio handles 409 by switching to existing song
✅ AI separator backend validates prerequisites for karaoke (vocals + transcription must exist)
```

---

## AI separator backend Console Output (Expected)

### Normal Upload:
```
INFO:app:Request: POST /upload from 127.0.0.1
Processing with demucs model
Processing complete
INFO:werkzeug:127.0.0.1 - - [21/Oct/2025 08:00:00] "POST /upload HTTP/1.1" 200 -
```

### Duplicate Upload:
```
INFO:app:Request: POST /upload from 127.0.0.1
Duplicate upload detected: Artist - Song.mp3 (existing file_id: abc-123)
INFO:werkzeug:127.0.0.1 - - [21/Oct/2025 08:00:00] "POST /upload HTTP/1.1" 409 -
```

### Skip Existing Output:
```
INFO:app:Request: POST /process/demucs/abc-123 from 127.0.0.1
Processing abc-123 with demucs model
Output already exists for demucs: C:\...\outputs\abc-123\vocals.mp3
INFO:werkzeug:127.0.0.1 - - [21/Oct/2025 08:00:00] "POST /process/demucs/abc-123 HTTP/1.1" 200 -
```

### Karaoke Without Prerequisites:
```
INFO:app:Request: POST /process/karaoke/abc-123 from 127.0.0.1
Processing abc-123 with karaoke model
INFO:werkzeug:127.0.0.1 - - [21/Oct/2025 08:00:00] "POST /process/karaoke/abc-123 HTTP/1.1" 400 -
```

---

## Files Modified

1. **AI separator backend:**
   - `app.py` - Added 3 helper functions + updated `/upload` and `/process` endpoints
   - Dependencies: `pip install transformers mutagen`

2. **Lion's Roar Studio:**
   - `context/AppContext.tsx` - Added 409 handling in upload flow

3. **Test Script:**
   - `test_duplicate_detection.py` - Automated test for duplicate + skip logic

---

## Next Steps

1. ✅ **Test duplicate upload** via frontend UI
2. ✅ **Test karaoke generation** end-to-end (Demucs → Whisper → Karaoke)
3. ⚠️ **Implement UI button disabling** based on existing outputs (Task 6)
4. ✅ **Verify no errors** in backend console for mutagen/transformers

---

**All critical bugs fixed! System now prevents duplicate uploads and skips redundant processing.** 🎉
