# Lion's Roar Studio-AI separator backend Sync Debugging Guide

## 🚨 Current Lion's Roar Studio Errors

### Error 1: "Invalid audio URL format"
**Location:** ScoreboardWindow.tsx:156 in handleDetectKey()
**Error Type:** Error thrown by frontend validation

**Possible Causes:**
1. Lion's Roar Studio is trying to send a URL instead of file_id
2. Lion's Roar Studio is sending incorrect data structure
3. Audio URL validation on frontend is too strict

**AI separator backend Expectation:**
```
POST /process/pitch_analysis/<file_id>
(file_id should be UUID from /upload response)
```

### Error 2: "Analysis failed: INTERNAL SERVER ERROR"
**Location:** ScoreboardWindow.tsx:206 in handlePitchAnalysis()
**Status Code:** 500 from backend
**Root Cause:** ✅ FIXED - matplotlib was missing

Now that matplotlib is installed, this should be resolved.

---

## 📊 Expected Lion's Roar Studio Flow

### Current (Error Flow)
```
Lion's Roar Studio → /process/pitch_analysis/5f925d8a... 
   ❌ Receives 500 error
   ❌ "Invalid audio URL format" error shown to user
```

### Correct (Should Be)
```
1. User uploads audio file
   POST /upload
   ✅ Response: { "file_id": "5f925d8a..." }

2. Lion's Roar Studio stores file_id
   const fileId = "5f925d8a..."

3. Lion's Roar Studio requests pitch analysis
   POST /process/pitch_analysis/5f925d8a
   Body: { "model_variant": "enhanced_chroma" }
   
   ✅ Response: {
     "file_id": "5f925d8a...",
     "model": "pitch_analysis",
     "status": "completed",
     "result": {
       "model": "enhanced_chroma",
       "detected_key": "C major",
       "confidence": 0.87,
       "analysis_file": "pitch_analysis_enhanced_chroma.json",
       "dominant_pitches": ["C", "E", "G"]
     }
   }
```

---

## 🔍 Lion's Roar Studio Code Issues to Check

### In ScoreboardWindow.tsx:126 (handleDetectKey)

**Issue: Where does the error "Invalid audio URL format" come from?**

Check if frontend code has this validation:
```javascript
// ❌ WRONG - This would cause the error
if (!audioURL.startsWith('http')) {
  throw new Error('Invalid audio URL format');
}

// ✓ CORRECT - Should use file_id instead
const fileId = selectedSong.fileId;
if (!fileId) {
  throw new Error('No file ID available');
}
```

**Symptoms showing need to check frontend:**
1. Error: "Invalid audio URL format" suggests frontend is trying to validate a URL
2. This means frontend might be storing audio URLs instead of file_ids
3. AI separator backend doesn't accept URLs - it needs file_ids

---

## 🧪 Test Cases to Verify Sync

### Test 1: Health Check (Verify AI separator backend Running)
```bash
curl http://localhost:5000/health

Expected Response:
{
  "status": "healthy",
  "message": "AI Model AI separator backend with WebSocket support is running",
  "available_models": ["demucs", "whisper", "musicgen", "pitch_analysis", "gemma_3n"],
  "websocket_support": true
}
```

**Lion's Roar Studio Should:**
- Show "AI separator backend Connected" when this succeeds
- Show error message if this fails

---

### Test 2: Upload File (Get file_id)
```bash
curl -X POST -F "file=@sample.mp3" http://localhost:5000/upload

Expected Response:
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "sample.mp3",
  "size": 3145728,
  "message": "File uploaded successfully"
}
```

**Lion's Roar Studio Should:**
- Extract and store `file_id`
- NOT use filename as ID
- NOT create URL from filename

---

### Test 3: Pitch Analysis (Use file_id from Test 2)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"model_variant": "enhanced_chroma"}' \
  http://localhost:5000/process/pitch_analysis/550e8400-e29b-41d4-a716-446655440000

Expected Response:
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "model": "pitch_analysis",
  "status": "completed",
  "result": {
    "model": "enhanced_chroma",
    "detected_key": "C major",
    "confidence": 0.92,
    "analysis_file": "pitch_analysis_enhanced_chroma.json",
    "dominant_pitches": ["C", "E", "G"],
    "output_dir": "/outputs/550e8400-e29b-41d4-a716-446655440000"
  },
  "message": "pitch_analysis processing completed successfully"
}
```

**Lion's Roar Studio Should:**
- Display detected_key
- Display confidence percentage
- Display dominant_pitches as chord
- Handle any errors gracefully

---

## 🛠️ Lion's Roar Studio Implementation Checklist

### Component State Management
- [ ] Store `uploadedFileId` after upload
- [ ] Clear `uploadedFileId` when new file uploaded
- [ ] Don't store audio URLs in state
- [ ] Store model selection separately from file data

### Error Handling
- [ ] Remove "Invalid audio URL format" error (backend doesn't use URLs)
- [ ] Add specific error for "No file uploaded" scenario
- [ ] Parse backend error responses (500 errors now resolved)
- [ ] Display user-friendly error messages

### Request Structure
```javascript
// ✓ CORRECT
const response = await fetch(
  `http://localhost:5000/process/pitch_analysis/${fileId}`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model_variant: 'enhanced_chroma'
    })
  }
);

// ❌ WRONG - Don't do this
await fetch('http://localhost:5000/process/pitch_analysis', {
  body: JSON.stringify({
    audioUrl: 'http://example.com/song.mp3',  // ❌ Not supported
    fileId: 'abc123'  // ❌ Should be in URL path
  })
});
```

### Response Handling
```javascript
// ✓ CORRECT
const data = await response.json();
if (response.ok) {
  const detectedKey = data.result.detected_key;
  const confidence = data.result.confidence;
  // Use data
} else {
  console.error(data.error); // AI separator backend error message
}

// ❌ WRONG - Assuming specific response structure
const detectedKey = data.detected_key;  // It's nested in result
```

---

## 📋 AI separator backend Response Structure All Models

### Response Wrapper (All Endpoints)
```json
{
  "file_id": "uuid or session_id",
  "model": "model_name",
  "status": "completed or error",
  "result": {
    // Model-specific result data
  },
  "message": "Human-readable message"
}
```

### Error Response (All Endpoints)
```json
{
  "error": "Error message",
  "details": "Optional detailed info"
}
```

**Lion's Roar Studio Must Always Check:**
1. HTTP Status Code (200 = success, 500 = error)
2. JSON response structure
3. Presence of `result` field
4. Nested data under `result`, not top-level

---

## 🎯 Quick Fixes for Lion's Roar Studio

### Fix 1: Remove Invalid URL Validation
**File:** ScoreboardWindow.tsx:126
```javascript
// Remove this validation
if (!audioURL.startsWith('http')) {
  throw new Error('Invalid audio URL format');  // ❌ DELETE
}

// Replace with file_id check
if (!fileId) {
  throw new Error('No audio file uploaded');
}
```

### Fix 2: Use Correct Endpoint Path
**File:** ScoreboardWindow.tsx:189 (handlePitchAnalysis)
```javascript
// Verify endpoint is exactly:
const endpoint = `http://localhost:5000/process/pitch_analysis/${fileId}`;
// NOT: /process/pitch_analysis/{fileId}
// NOT: /pitch_analysis/{fileId}
```

### Fix 3: Send Correct Request Body
**File:** ScoreboardWindow.tsx:189
```javascript
// Verify body is exactly:
const body = JSON.stringify({
  model_variant: 'enhanced_chroma'
});
// NOT: { variant: ... }
// NOT: { model: ... }
```

### Fix 4: Extract Result Correctly
**File:** ScoreboardWindow.tsx:206 (handlePitchAnalysis response)
```javascript
// AI separator backend returns nested structure:
const data = await response.json();

// CORRECT: Access nested result
const detectedKey = data.result.detected_key;
const confidence = data.result.confidence;

// WRONG: Direct access
const detectedKey = data.detected_key;  // undefined
```

---

## ✅ Verification After Fixes

### Test in Browser DevTools Console
```javascript
// 1. Test upload
const uploadRes = await fetch('http://localhost:5000/upload', {
  method: 'POST',
  body: new FormData() // Add file here
});
const uploadData = await uploadRes.json();
console.log('File ID:', uploadData.file_id); // Should be UUID

// 2. Test pitch analysis
const fileId = uploadData.file_id;
const analysisRes = await fetch(
  `http://localhost:5000/process/pitch_analysis/${fileId}`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_variant: 'enhanced_chroma' })
  }
);
const analysisData = await analysisRes.json();
console.log('Result:', analysisData.result);

// 3. Check structure
console.log('Detected Key:', analysisData.result.detected_key);
console.log('Confidence:', analysisData.result.confidence);
console.log('Pitches:', analysisData.result.dominant_pitches);
```

---

## 📞 Still Getting 500 Errors?

If still seeing 500 errors after fixes:

1. **Check AI separator backend Logs:**
   - Look at Flask terminal output
   - Should show "Processing pitch_analysis..." message
   - Any exceptions will be printed

2. **Verify Dependencies:**
   ```bash
   pip list | grep matplotlib
   # Should show: matplotlib 3.x.x
   ```

3. **Test AI separator backend Directly:**
   ```bash
   # Use curl to test without frontend
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"model_variant": "enhanced_chroma"}' \
     http://localhost:5000/process/pitch_analysis/test-id-123
   ```

4. **Enable Debug Mode:**
   In app.py, temporarily set `DEBUG=True` to see detailed error traces

---

## 📈 Lion's Roar Studio-AI separator backend Compatibility Matrix

| Feature | AI separator backend | Lion's Roar Studio | Status |
|---------|---------|----------|--------|
| File Upload | ✅ /upload | ? | ⚠️ Verify |
| Pitch Analysis | ✅ /process/pitch_analysis | Error | ⚠️ Fix needed |
| Demucs | ✅ /process/demucs | ? | ⚠️ Verify |
| Whisper | ✅ /process/whisper | ? | ⚠️ Verify |
| MusicGen | ✅ /process/musicgen | ? | ⚠️ Verify |
| Gemma 3N | ✅ /process/gemma_3n | ? | ⚠️ Verify |
| Error Handling | ✅ Standard format | ? | ⚠️ Verify |
| CORS | ✅ All origins | ? | ⚠️ Verify |

---

## 🎯 Next Steps

1. ✅ **DONE:** Fixed matplotlib dependency on backend
2. **TODO:** Test pitch analysis with curl command above
3. **TODO:** Check frontend code for URL validation logic
4. **TODO:** Fix "Invalid audio URL format" error source
5. **TODO:** Verify file_id flow (upload → store → use in process)
6. **TODO:** Test all other models similarly
7. **TODO:** Implement proper error displays
8. **TODO:** Add progress tracking for long operations
