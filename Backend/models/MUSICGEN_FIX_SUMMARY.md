<!-- Pointer: moved to /part of AI separator backend/musicgen/MUSICGEN_GUIDE.md -->

See canonical copy at: `/part of AI separator backend/musicgen/MUSICGEN_GUIDE.md`
> This summary has been moved to the part of AI separator backend area.

See the canonical MusicGen guide at:

- /part of AI separator backend/musicgen/MUSICGEN_GUIDE.md

> NOTE: Archived. Use the canonical guide at `/part of AI separator backend/musicgen/MUSICGEN_GUIDE.md`.

If you need this file to remain at the old path for scripts, please open an issue with the script path and we'll add a compatibility pointer.
# MusicGen 500 Internal Server Error - Fixed ✅

## Problem Summary
When attempting to use MusicGen for music generation, the frontend received a **500 INTERNAL SERVER ERROR** from the backend. The request was properly routed and authentication passed, but the processing failed on the server side.

---

## Root Causes Identified

### 1. **Incorrect MusicGen Model Loading**
**Location:** `server/main.py` line 514
**Issue:** Used `MusicGen.get_mocked_model(variation)` which doesn't exist in the audiocraft library
```python
# WRONG
model = MusicGen.get_mocked_model(variation)

# CORRECT  
model = MusicGen.get_model(variation)
```

### 2. **Missing Prompt in Request Payload**
**Location:** Lion's Roar Studio - `AdvancedToolsWindow.tsx` and backend coordination
**Issue:** 
- User enters music description (prompt) in frontend dialog
- Lion's Roar Studio passes this as the `variation` parameter (wrong parameter name)
- AI separator backend never receives the prompt text
- MusicGen tries to generate with empty/default prompt

**Solution:** 
- Lion's Roar Studio now explicitly passes `prompt` in the request body: `{ prompt: userDescription, variation: 'medium' }`
- AI separator backend extracts `prompt` from request JSON and passes to `process_with_musicgen()`

### 3. **Incomplete Processing Pipeline**
**Location:** `server/main.py` - `process_audio_async()` function
**Issue:** The function signature didn't accept a prompt parameter, so it couldn't be passed from route handler to processing function
**Solution:** Added `prompt: str = None` parameter to `process_audio_async()` and pass through to `process_with_musicgen()`

---

## Changes Made

### AI separator backend Changes (`server/main.py`)

#### 1. Fixed MusicGen Model Loading (line 514)
```python
# Before
model = MusicGen.get_mocked_model(variation)

# After
model = MusicGen.get_model(variation)
```

#### 2. Updated `process_audio_async()` Signature (line 793-813)
Added `prompt` parameter to pipeline:
```python
def process_audio_async(
    file_path: str,
    file_id: str,
    model: str,
    variation: str = None,
    prompt: str = None  # NEW: Accept prompt parameter
):
    # ... pass prompt to MusicGen
    elif model == 'musicgen':
        process_with_musicgen(
            file_path, file_id, variation, prompt or ''
        )
```

#### 3. Updated `/process/<model>/<file_id>` Route (line 970-990)
Extract prompt from request and pass to background thread:
```python
# Extract both variation and optional prompt from request
data = request.get_json() or {}
variation = data.get('variation', AVAILABLE_MODELS[model]['default_variation'])
prompt = data.get('prompt', '') if model == 'musicgen' else None

# Pass prompt to processing thread
thread = threading.Thread(
    target=process_audio_async,
    args=(file_path, file_id, model, variation, prompt)
)

# Store prompt in job metadata
if prompt is not None:
    jobs[file_id]['prompt'] = prompt
```

### Lion's Roar Studio Changes (`context/AppContext.tsx`)

#### Updated Request Payload Building (line 593-613)
Special handling for MusicGen to pass prompt correctly:
```typescript
// Build payload - for MusicGen, 'variation' is actually the prompt
const processPayload: any = {};
if (tool === 'musicgen') {
  // For MusicGen, selectedVariation is the user's prompt
  processPayload.prompt = selectedVariation || '';
  processPayload.variation = 'medium'; // default model variation
} else if (selectedVariation) {
  processPayload.variation = selectedVariation;
}

// Send with proper content-type header
const processResponse = await fetch(
  `${API_BASE_URL}/process/${selectedModel}/${file_id}`,
  { 
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(processPayload)
  }
);
```

---

## Data Flow (After Fix)

### User Action Flow
```
1. User clicks "AI Music Generation" in Advanced Tools
2. Prompted to enter music description: "upbeat jazz piano"
3. Lion's Roar Studio calls:
   processSongWithAdvancedTool(songId, 'musicgen', 'musicgen', 'upbeat jazz piano')
   
   - songId: unique song identifier
   - tool: 'musicgen' (determines which model to use)
   - model: 'musicgen' (explicit model name)
   - variation: 'upbeat jazz piano' (passed as prompt in special handling)
```

### Request Chain
```
Lion's Roar Studio:
  1. Upload audio to /upload
     ↓ Get file_id
  2. POST /process/musicgen/{file_id}
     Body: {
       prompt: "upbeat jazz piano",
       variation: "medium"
     }

AI separator backend:
  3. Extract prompt and variation from request
  4. Create background thread:
     process_audio_async(file_path, file_id, 'musicgen', 'medium', 'upbeat jazz piano')
  5. MusicGen processing:
     - Load model: MusicGen.get_model('medium')
     - Set duration: 15 seconds (for medium)
     - Generate: model.generate(['upbeat jazz piano'])
     - Save to: PROCESSED_FOLDER/{file_id}/generated_music.wav
  6. Update job status to 'completed'

Lion's Roar Studio Polling:
  7. GET /status/{file_id}
     Response: { status: 'completed', outputs: { generated: '/path/to/generated_music.wav' } }
```

---

## API Contract Update

### Request Format
**Endpoint:** `POST /process/musicgen/{file_id}`
**Body:**
```json
{
  "prompt": "music description from user",
  "variation": "small|medium|large"
}
```

**Response (Initial):**
```json
{
  "message": "Processing started with musicgen",
  "file_id": "...",
  "status": "queued",
  "model": "musicgen",
  "variation": "medium"
}
```

**Response (Status Check):**
```json
{
  "status": "completed",
  "progress": "Music generation completed successfully",
  "outputs": {
    "generated": "/path/to/generated_music.wav"
  }
}
```

---

## Testing the Fix

### Step 1: Verify AI separator backend
```bash
# Check MusicGen is installed
pip show audiocraft torch torchaudio

# Start server
cd server
python main.py
```

### Step 2: Manual API Test
```bash
# Upload audio file
curl -X POST http://localhost:5000/upload \
  -F "file=@test.mp3"

# Should return: { "file_id": "xxx" }

# Process with MusicGen
curl -X POST http://localhost:5000/process/musicgen/xxx \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "upbeat jazz piano solo",
    "variation": "medium"
  }'

# Check status
curl http://localhost:5000/status/xxx
```

### Step 3: Lion's Roar Studio UI Test
1. Open Advanced Tools window
2. Click "AI Music Generation"
3. Enter prompt: "upbeat jazz piano solo"
4. Observe:
   - ✅ Request sent successfully (Network tab shows 200 response from /process/musicgen)
   - ✅ Background processing starts (status changes to 'processing')
   - ✅ File generated and saved
   - ✅ Success notification appears

---

## Performance Notes

- **Model Variations:**
  - `small`: 8 seconds, ~30-60s generation time, ~12GB GPU
  - `medium`: 15 seconds, ~1-2 minutes, ~16GB GPU  
  - `large`: 30 seconds, ~3-5 minutes, ~20GB GPU

- **First Run:** Models download automatically (10-30+ minutes for initial setup)
- **Subsequent Runs:** Models cached locally, faster startup

---

## Verification Checklist

- ✅ MusicGen model loading uses `get_model()` not `get_mocked_model()`
- ✅ Lion's Roar Studio passes prompt in request body as `{ prompt: "...", variation: "..." }`
- ✅ AI separator backend extracts prompt from request JSON
- ✅ AI separator backend passes prompt through processing pipeline
- ✅ Job metadata stores prompt for debugging/logging
- ✅ Error handling preserved for ImportError and general exceptions
- ✅ Processing status tracked throughout execution
- ✅ Output saved to standard location: `PROCESSED_FOLDER/{file_id}/generated_music.wav`

---

## Files Modified

| File | Changes | Type |
|------|---------|------|
| `server/main.py` | Fixed MusicGen model call, updated pipeline | Bug Fix |
| `server/main.py` | Added prompt extraction in /process route | Feature |
| `context/AppContext.tsx` | Added special handling for MusicGen prompt | Bug Fix |

---

## Next Steps

1. **Install Dependencies** (if not already done):
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. **Test MusicGen Through UI:**
   - Advanced Tools → AI Music Generation
   - Enter music description
   - Verify processing and output

3. **Monitor Logs:**
   - Check server console for processing progress
   - Verify file is saved to correct location

4. **Test Other Tools:**
   - Pitch Analysis (similar fixes may apply)
   - Gemma 3N analysis

---

**Status:** ✅ Ready for testing!
