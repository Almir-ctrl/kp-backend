# Backend-Lion's Roar Studio Sync - Visual Architecture & Data Flow

## 🏗️ Overall Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ScoreboardWindow.tsx ⚠️ NEEDS FIXES                  │   │
│  │  • handleDetectKey() [Line 126]                      │   │
│  │  • handlePitchAnalysis() [Line 189]                  │   │
│  │  • Response parsing [Line 206]                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                    HTTP/JSON (CORS)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               BACKEND (Flask) ✅ READY                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ API Server (5000)                                    │   │
│  │  • /upload                                           │   │
│  │  • /process/<model>/<file_id>                        │   │
│  │  • /download/<model>/<file_id>/<filename>            │   │
│  │  • /status/<file_id>                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AI Models (5)                                        │   │
│  │  ✅ Demucs (Audio Separation)                       │   │
│  │  ✅ Whisper (Transcription)                         │   │
│  │  ✅ MusicGen (Generation)                           │   │
│  │  ✅ Pitch Analysis (Key Detection) [FIXED]          │   │
│  │  ✅ Gemma 3N (Audio Analysis)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ File System                                          │   │
│  │  📁 /uploads/     → User uploaded files              │   │
│  │  📁 /outputs/     → Processing results               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Current Request/Response Flow

### ❌ Current Flow (With Errors)

```
Lion's Roar Studio (React)
    │
    ├─→ User selects audio file
    │
    ├─→ ❌ Validates: if (!audioURL.startsWith('http'))
    │                    throw "Invalid audio URL format" ← ERROR HERE!
    │
    ├─→ Throws error before request even sent
    │
    └─→ User sees: "Error detecting song key: Invalid audio URL format"
```

### ✅ Correct Flow (After Lion's Roar Studio Fix)

```
Lion's Roar Studio (React)
    │
    ├─→ 1. User uploads audio file
    │      POST /upload
    │      ▼
    │      Response: { "file_id": "abc123..." }
    │
    ├─→ 2. Store file_id in state: uploadedFileId = "abc123..."
    │
    ├─→ 3. User clicks "Detect Key"
    │      GET file_id from state
    │      POST /process/pitch_analysis/abc123
    │      Header: { "Content-Type": "application/json" }
    │      Body: { "model_variant": "enhanced_chroma" }
    │      ▼
    │      Response: {
    │        "status": "completed",
    │        "result": {
    │          "detected_key": "C major",
    │          "confidence": 0.87
    │        }
    │      }
    │
    ├─→ 4. Parse nested response
    │      detectedKey = data.result.detected_key
    │      confidence = data.result.confidence
    │
    └─→ 5. Display to user: "Key: C major (87% confidence)"
```

---

## 🔄 Data Flow Comparison

### WRONG (Current Lion's Roar Studio) ❌
```
┌─ Lion's Roar Studio ─────────────────┐
│                            │
│ audioURL = "http://..."    │  ← Wrong! Backend doesn't accept URLs
│                            │
│ Request:                   │
│ POST /process/pitch_analysis │  ← Wrong! File_id not in path
│ {                          │
│   url: audioURL            │  ← Wrong! Field name is model_variant
│ }                          │
│                            │
│ Response parsing:          │
│ key = data.detected_key    │  ← Wrong! It's data.result.detected_key
│                            │
└────────────────────────────┘
```

### CORRECT (After Fix) ✅
```
┌─ Lion's Roar Studio ─────────────────────┐
│                                │
│ fileId = "af363c28-..."        │  ← Correct! From upload response
│                                │
│ Request:                       │
│ POST /process/pitch_analysis/af363c28 │  ← Correct! File_id in path
│ {                              │
│   model_variant: "enhanced_chroma" │  ← Correct! Field name
│ }                              │
│                                │
│ Response parsing:              │
│ key = data.result.detected_key │  ← Correct! Nested structure
│                                │
└────────────────────────────────┘
```

---

## 📤 Upload & Processing Workflow

### Step 1: Upload File
```
Lion's Roar Studio                          Backend
   │                                │
   ├─ POST /upload ────────────────→│
   │  (multipart/form-data)         │
   │                                ├─ Save to /uploads/
   │                                ├─ Generate UUID
   │  ←──────── Response ───────────┤
   │  {                             │
   │    "file_id": "abc123...",    │← SAVE THIS!
   │    "filename": "song.mp3"     │
   │  }                             │
   │                                │
   └─ Store file_id in state        │
```

### Step 2: Process with Model
```
Lion's Roar Studio                          AI separator backend
   │                                │
  ├─ POST /process/               │
  │   pitch_analysis/abc123 ──────→│
   │  {                             │
   │    "model_variant":           │
   │    "enhanced_chroma"          │
   │  }                             │
   │                                ├─ Load file from /uploads/abc123
   │                                ├─ Initialize model
   │                                ├─ Extract features
   │                                ├─ Detect key
   │                                ├─ Save to /outputs/abc123
   │  ←──────── Response ───────────┤
   │  {                             │
   │    "status": "completed",     │
   │    "result": {               │
   │      "detected_key":         │
   │        "C major",            │
   │      "confidence": 0.87      │
   │    }                         │
   │  }                           │
   │                              │
   └─ Display to user             │
```

---

## 🔧 Required Lion's Roar Studio Changes

### Change 1: Remove Invalid URL Validation
```diff
Location: ScoreboardWindow.tsx:126

- if (!audioURL.startsWith('http')) {
-   throw new Error('Invalid audio URL format');
- }
+ if (!fileId) {
+   throw new Error('No file uploaded');
+ }
```

### Change 2: Fix Endpoint Path
```diff
Location: ScoreboardWindow.tsx:189

- const response = await fetch('/process/pitch_analysis', {
+ const response = await fetch(
+   `http://localhost:5000/process/pitch_analysis/${fileId}`,
  {
```

### Change 3: Fix Request Body
```diff
Location: ScoreboardWindow.tsx:189

  body: JSON.stringify({
-   url: audioURL
+   model_variant: 'enhanced_chroma'
  })
```

### Change 4: Fix Response Parsing
```diff
Location: ScoreboardWindow.tsx:206

- const detectedKey = data.detected_key;
- const confidence = data.confidence;
+ const detectedKey = data.result.detected_key;
+ const confidence = data.result.confidence;
```

---

## 📋 File_ID Flow Diagram

```
                User Action
                    │
                    ▼
    ┌──────────────────────────────┐
    │ User selects audio file      │
    │ & clicks upload              │
    └──────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ Lion's Roar Studio: POST /upload       │
    │ (send audio file)            │
    └──────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ AI separator backend: Generate UUID       │
    │ Save to /uploads/UUID        │
    │ Return file_id: UUID         │
    └──────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ Lion's Roar Studio: Store file_id      │
    │ in React state               │
    │ uploadedFileId = UUID        │
    └──────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ User clicks process button   │
    │ (detect key, separate, etc)  │
    └──────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ Lion's Roar Studio: POST /process/.../ │
    │ pitch_analysis/{file_id}     │
    │ (use stored file_id)         │
    └──────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ AI separator backend: Find file in        │
    │ /uploads/{file_id}           │
    │ Process & save to            │
    │ /outputs/{file_id}           │
    │ Return results               │
    └──────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ Lion's Roar Studio: Display results    │
    │ to user                      │
    └──────────────────────────────┘
```

---

## 🧪 Test Sequence Diagram

```
Lion's Roar Studio                AI separator backend
   │                      │
   │─ GET /health ───────→│ (Check if backend running)
   │                      │
   │←─── 200 OK ─────────│
   │                      │
   │─ POST /upload ──────→│ (Upload audio file)
   │  [multipart/data]    │
   │                      ├─ Generate UUID
   │                      ├─ Save file
   │                      │
   │←─── { "file_id" } ──│ (Return file_id)
   │                      │
   │─ POST /process/ ────→│ (Request processing)
   │  pitch_analysis/{id} │
   │  { model_variant }   │
   │                      ├─ Load file
   │                      ├─ Extract features
   │                      ├─ Detect key
   │                      │
   │←─── { result } ─────│ (Return analysis)
   │                      │
   │ (Display results)    │
   │                      │
```

---

## 📊 Model Configuration Summary

### Current AI separator backend Models
```
┌─ Pitch Analysis (FIXED ✅) ─────────┐
│                                      │
│ Endpoint: /process/pitch_analysis    │
│ File_id: Required (in URL path)      │
│ Default: enhanced_chroma             │
│ Variants:                            │
│   • basic_chroma                     │
│   • enhanced_chroma (default)        │
│   • librosa_chroma                   │
│                                      │
│ Request:                             │
│   POST /process/pitch_analysis/<id>  │
│   { "model_variant": "..." }         │
│                                      │
│ Response:                            │
│   {                                  │
│     "result": {                      │
│       "detected_key": "C major",     │
│       "confidence": 0.87,            │
│       "dominant_pitches": [...]      │
│     }                                │
│   }                                  │
└──────────────────────────────────────┘

┌─ Other Models (Ready) ─────────────────┐
│                                         │
│ Demucs       → /process/demucs         │
│ Whisper      → /process/whisper        │
│ MusicGen     → /process/musicgen       │
│ Gemma 3N     → /process/gemma_3n      │
│                                         │
│ All follow same pattern:               │
│ POST /process/{model}/{file_id}        │
│ { "model_variant": "..." }             │
└─────────────────────────────────────────┘
```

---

## ✅ Verification Checklist

### AI separator backend Status
- [x] Flask server running
- [x] All 5 models configured
- [x] matplotlib dependency installed
- [x] librosa tempo function fixed
- [x] File upload working
- [x] CORS enabled
- [x] Error handling implemented

### Lion's Roar Studio Status (TO DO)
- [ ] Remove invalid URL validation
- [ ] Fix endpoint paths
- [ ] Fix request body format
- [ ] Fix response parsing
- [ ] Test with curl commands
- [ ] Verify all 5 models work
- [ ] Test error handling

---

## 🚀 Deployment Readiness

```
BACKEND:    ████████████████████ ✅ READY (100%)
FRONTEND:   ████░░░░░░░░░░░░░░░░ ⚠️  PENDING (20%)

Action Items:
  AI separator backend:   ✅ No changes needed
  Lion's Roar Studio:  ⚠️  4 code fixes required (~30 min work)
  Testing:   ⚠️  Full integration test (~1 hour)
  Deploy:    ⏳ Ready after frontend fixes
```

---

## 📞 Quick Reference

| What | Where | Solution |
|------|-------|----------|
| AI separator backend not running | Terminal | `python app.py` |
| URL validation error | Line 126 | Remove URL check |
| Wrong endpoint | Line 189 | Use `/process/{model}/{fileId}` |
| Wrong response | Line 206 | Access `data.result.*` |
| Test endpoint | Terminal | Use curl commands (see /AI separator backend/ANALYSIS_SUMMARY.md) |

All documentation and test scripts have been created. AI separator backend is ready for frontend integration! 🎉
