# Changelog — server

All noteworthy changes and troubleshooting steps for the `server` proxy-audio component.

## 2025-10-21 — Duplicate Detection & Smart Processing

### Added
- **Duplicate Upload Prevention**: `check_duplicate_upload(filename)` helper function
  - Searches all `outputs/*/metadata.json` files for matching `original_filename`
  - Returns **409 Conflict** with existing `file_id` if duplicate found
  - Response format: `{"error": "Song already exists", "file_id": "uuid", "existing": true}`
  - Lion's Roar Studio handles 409 by switching to existing song instead of re-uploading
  - Prevents wasted storage and redundant processing

- **Smart Output Detection**: `check_output_exists(file_id, output_type)` helper function
  - Checks if specific outputs already exist before processing
  - Supported types: `vocals`, `instrumental`, `transcription`, `karaoke`
  - Returns file path if output exists, `None` otherwise
  - Used by `/process` endpoint to skip redundant work

- **Process Skip Logic**: Automatic detection and skip for existing outputs
  - Before Demucs processing → checks for `vocals.mp3` or `vocals.wav`
  - Before Whisper processing → checks for `transcription_base.txt` or `.json`
  - Returns **200 OK** with `{"skipped": true, "existing_output": "filename"}` if output exists
  - Instant return instead of re-processing (saves time and GPU resources)

### Fixed
- **Critical: Karaoke API Mismatch**: `/process/karaoke/{file_id}` now passes required parameters
  - Issue: `TypeError: KaraokeProcessor.process() missing 2 required positional arguments: 'vocals_path' and 'transcription_text'`
  - Root cause: Generic processor call didn't provide karaoke-specific dependencies
  - Solution: Special handling for karaoke model:
    - Reads `vocals.mp3` from `outputs/{file_id}/`
    - Reads `transcription_base.txt` or `.json` from `outputs/{file_id}/`
    - Reads `metadata.json` for artist/song_name
    - Validates prerequisites exist before calling processor
  - Returns **400 Bad Request** if vocals or transcription missing with clear error message
  - Impact: Karaoke generation now works end-to-end without manual path passing

- **Missing Dependencies**: Installed required packages
  - `mutagen` - MP3 metadata (ID3 tags) for karaoke audio files
  - Error resolved: `ModuleNotFoundError: No module named 'mutagen'`
  - Package already present: `transformers` (Gemma 3N), `librosa`, `soundfile`

### Changed
- **Upload Endpoint**: `/upload` and `/upload/<model_name>` now check for duplicates
  - Duplicate check happens BEFORE file save (early exit)
  - Console log: `Duplicate upload detected: {filename} (existing file_id: {uuid})`
  - Lion's Roar Studio receives 409 status and switches to existing song

- **Process Endpoint**: `/process/<model>/<file_id>` now validates and skips
  - Karaoke model: Validates vocals + transcription exist, reads them automatically
  - Demucs/Whisper: Checks for existing output, returns cached result if found
  - Console log: `Output already exists for {model}: {path}`
  - Skipped responses include `"skipped": true` flag for frontend handling

### Lion's Roar Studio Changes (AppContext.tsx)
- **409 Conflict Handling**: Upload flow now detects duplicate songs
  - Notification: ⚠️ "Song already exists! Opening existing version."
  - Searches library for existing song by `file_id`
  - Calls `setCurrentSong()` to switch to existing song
  - Falls back to `fetchSongsFromBackend()` if not in local cache
  - No re-upload or re-processing triggered

### Technical Details

**Duplicate Detection Algorithm:**
```python
def check_duplicate_upload(filename):
    # Iterate through outputs/*/ directories
    # Read metadata.json in each
    # Compare original_filename field
    # Return file_id (directory name) if match found
```

**Skip Logic Flow:**
```python
# Before processing:
if model_name in ['demucs', 'whisper']:
    existing = check_output_exists(file_id, output_map[model_name])
    if existing:
        return 200 with existing files (no processing)

# For karaoke:
if model_name == 'karaoke':
    vocals = check_output_exists(file_id, 'vocals')
    transcription = check_output_exists(file_id, 'transcription')
    if not vocals or not transcription:
        return 400 Bad Request with error message
```

**Console Output Examples:**
```
# Duplicate upload:
Duplicate upload detected: Artist - Song.mp3 (existing file_id: abc-123)

# Skip existing output:
Output already exists for demucs: C:\...\outputs\abc-123\vocals.mp3
INFO:werkzeug:127.0.0.1 - - [21/Oct/2025 08:00:00] "POST /process/demucs/abc-123 HTTP/1.1" 200 -

Processing abc-123 with karaoke model
# (validates vocals/transcription exist, then proceeds)
```

### Performance Impact
- **Storage savings**: Duplicate files no longer saved to `uploads/` or `outputs/`
- **GPU usage**: No wasted GPU cycles on duplicate processing
- **User experience**: Instant feedback for duplicates, faster "already processed" responses

### Migration Notes
- **Breaking change**: None (all changes are additive)
- **Backwards compatible**: Existing `/upload` and `/process` API contracts unchanged
- **New response codes**: 
  - **409 Conflict** for duplicate uploads (frontend must handle)
  - **400 Bad Request** for karaoke without prerequisites (clear error messages)
- **New response fields**:
  - `"skipped": true` in skip responses
  - `"existing_output": "filename"` in skip responses

### Testing Recommendations
1. **Duplicate Upload Test**: Upload same file twice, verify 409 on second attempt
3. **Karaoke Prerequisites Test**: Try karaoke without vocals, verify 400 error message
4. **Karaoke End-to-End Test**: Demucs → Whisper → Karaoke, verify automatic file discovery
5. **Lion's Roar Studio Integration Test**: Verify 409 handling switches to existing song in UI

- Created: `DUPLICATE_DETECTION_COMPLETE.md` - Full implementation guide
- Test script: `test_duplicate_detection.py` - Automated test suite

---

## 2025-10-19 — Auto-Processing Fix: Demucs & Test UI
### Fixed
- **Critical**: Resolved Demucs and Gemma not auto-processing
  - Issue: `demucs` package was not installed in virtual environment
  - Solution: Installed demucs via install_python_packages
  - Impact: Audio separation now works in auto-processing pipeline
- **Test UI 404 Error**: Created test_progress.html and added Flask routes
  - Issue: No route to serve static test UI
  - Solution: Added `/test_progress.html` and `/static/<filename>` routes
  - Impact: Beautiful progress tracking UI now accessible

### Added
- **Test Progress UI**: `static/test_progress.html` (468 lines)
  - Drag-and-drop file upload
  - WebSocket connection status indicator
  - 4 animated progress bars (Upload, Separation, Transcription, Karaoke)
  - Real-time progress updates with visual states (waiting/processing/complete/error)
  - Download links on completion
  - Error handling with user-friendly messages
- **Import Test Script**: `test_imports.py`
  - Comprehensive dependency verification
  - Tests all critical imports (demucs, transformers, torch, librosa, etc.)
  - Validates processor creation
- **Documentation**: `AUTO_PROCESSING_FIX.md`
  - Complete resolution documentation
  - Auto-processing flow explanation
  - Troubleshooting guide
  - Performance notes

### Changed
- **app.py**: Added static file serving routes
  - Route: `/test_progress.html` - Serves main test UI
  - Route: `/static/<filename>` - Serves any static file

### Technical Details
**Missing Package Installed:**
- `demucs` - Audio source separation library

**Auto-Processing Pipeline Verified:**
1. ✅ Upload (100%) - File saved to uploads/
2. ✅ Separation (0-100%) - Demucs separates vocals/instrumentals
3. ✅ Transcription (0-100%) - Gemma 3n analyzes audio
4. ✅ Karaoke (0-100%) - Synced lyrics generation
5. ✅ Complete (100%) - Download links available

**Test UI Features:**
- WebSocket integration with Socket.IO client
- Responsive design with gradient background
- Progress bars with percentage display
- Stage status indicators (⏳ Waiting → 🔄 Processing → ✓ Complete → ❌ Error)
- File info display (name, size, type)
# Start server (always use this!)
.\start_app.ps1

# Test imports
```

### Verification
```
✅ demucs imported successfully
✅ All Gemma 3n dependencies working
✅ Flask-SocketIO working
✅ Test UI accessible
✅ Auto-processing pipeline operational
```

---

- **PowerShell Startup Script**: New `start_app.ps1` for reliable server startup
  - Automatically uses correct virtual environment (api/.venv)
  - Verifies all dependencies before starting
  - Creates venv if missing
  - Displays clear startup information and server URLs
  - Complete setup and usage instructions
  - API endpoint documentation
  - Performance notes and next steps
- **Flask-SocketIO**: Added to `requirements.txt` for WebSocket support
- **Critical**: Resolved "No module named 'transformers'" error when running app.py
  - Issue: Running `python app.py` used system Python instead of virtual environment
  - Impact: All Gemma 3n dependencies now available at runtime
- **HuggingFace Authentication**: Created `setup_hf_token.py` for easy token setup
  - Saves token to .env file
  - Sets environment variables automatically
### Changed
- **Recommended Startup Method**: Use `.\start_app.ps1` instead of `python app.py`
  - Ensures virtual environment is active
  - Prevents dependency import errors
  - Verifies setup before starting server

### Technical Details
**Virtual Environment Path:**
- `C:\Users\almir\AiMusicSeparator-Backend\api\.venv\`
- Python 3.13.5

**Startup Script Features:**
- Dependency verification: transformers, torch, librosa, soundfile, accelerate, sentencepiece
- Auto-install missing packages
- Environment info display
- Server URL display (localhost + network)
- Test UI link display

**Files Created:**
- `start_app.ps1` - PowerShell startup script
- `setup_hf_token.py` - HuggingFace authentication helper
- `QUICK_START.md` - Complete usage guide

### Usage
```powershell
# Start server (recommended)
.\start_app.ps1

# Verify Gemma setup
python verify_gemma.py

# Setup HuggingFace token
python setup_hf_token.py
```

---

## 2025-10-19 — Gemma 3n Dependencies Verification & Setup

### Added
- **Dependency Verification Script**: New `verify_gemma.py` comprehensive checker
  - Validates all Gemma 3n dependencies (transformers, torch, librosa, soundfile, accelerate, sentencepiece)
  - Tests audio processing capabilities with feature extraction
  - Attempts model loading and generation (optional if HF token available)
  - Provides detailed diagnostics and troubleshooting guidance
- **Setup Documentation**: Comprehensive `GEMMA_SETUP_GUIDE.md`
  - Step-by-step HuggingFace authentication guide
  - Model selection and configuration
  - Performance benchmarks and hardware requirements
  - Troubleshooting common issues
  - Quick checklist for setup verification
- **Missing Dependencies**: Added to `requirements.txt`
  - `sentencepiece` - Required for Gemma tokenization
  - `protobuf` - Required for model serialization

### Fixed
- Ensured all Gemma 3n dependencies are properly documented
- Added verification for gated model access requirements

### Technical Details
**Dependencies Verified:**
- ✅ transformers (4.57.1) - Hugging Face Transformers
- ✅ torch (2.9.0) - PyTorch
- ✅ librosa (0.11.0) - Audio processing
- ✅ soundfile (0.13.1) - Audio I/O
- ✅ accelerate (1.10.1) - Model loading optimization
- ✅ sentencepiece (0.2.1) - Tokenization

**Verification Script Tests:**
1. Dependency installation check
2. Audio processing capabilities (sine wave generation, feature extraction)
3. Model loading from HuggingFace (optional - requires authentication)

**Setup Requirements:**
- HuggingFace account and token
- Gemma license acceptance (gated model)
- 8GB+ VRAM for gemma-2-2b
- 10GB+ disk space for model cache

### Usage
```bash
# Verify dependencies
python verify_gemma.py

# Install missing dependencies
pip install -r requirements.txt

# Setup HuggingFace authentication
huggingface-cli login
# Or set environment variable
$env:HF_TOKEN="your_token_here"
```

### Notes
- Gemma models are **gated** and require HuggingFace authentication
- First-time model download can be 5-10 GB
- CPU inference works but is slower than GPU
- See `GEMMA_SETUP_GUIDE.md` for complete setup instructions

### Migration
No breaking changes. Gemma 3n will work automatically once:
1. Dependencies are installed (already done)
2. HuggingFace token is configured
3. Gemma license is accepted

## 2025-10-19 — Real-Time Processing Progress Feedback

### Added
- **WebSocket Progress Events**: Real-time progress updates during audio processing
  - New `processing_progress` event emitted via SocketIO
  - Stage-by-stage progress tracking (upload, separation, transcription, karaoke)
  - Percentage-based progress (0-100%) for each stage
  - Human-readable status messages for each update
  - Error reporting with detailed messages when stages fail
- **Progress Stages**:
  - `upload` - File upload complete (100%)
  - `separation` - Audio separation (Demucs) progress
  - `transcription` - AI transcription (Gemma 3n) progress
  - `karaoke` - Karaoke generation progress
  - `complete` - All processing finished
- **Interactive Demo**: New `test_progress.html` with beautiful UI
  - Drag-and-drop file upload
  - Real-time progress bars with animations
  - Stage-by-stage status indicators (waiting, processing, complete, error)
  - Connection status indicator
  - Download links when processing complete
- **Documentation**: Comprehensive `PROGRESS_FEEDBACK_GUIDE.md`
  - WebSocket event structure and examples
  - Lion's Roar Studio integration guides (JavaScript, React, Vue)
  - UI/UX recommendations
  - Testing and troubleshooting sections

### Changed
- Upload endpoint now emits progress events throughout processing pipeline
- Each processing stage emits start and completion events
- Error handling includes progress event with error field
- Non-blocking: Progress events don't affect HTTP response timing

### Technical Details
- **Event Structure**:
  ```json
  {
    "file_id": "abc123",
    "stage": "separation",
    "progress": 45,
    "message": "Separating audio tracks...",
    "error": null
  }
  ```
- **Event Frequency**: 1-3 events per stage (minimal overhead)
- **Connection**: Single WebSocket per client via Socket.IO
- **Scalability**: Supports multiple concurrent users

### Lion's Roar Studio Benefits
- **Better UX**: Users see exactly what's happening
- **No "Black Box"**: Transparent processing pipeline
- **Error Visibility**: Immediate feedback when something fails
- **Progress Bars**: Real loading indicators instead of spinners
- **Time Awareness**: Users know processing isn't stuck

### Migration
No breaking changes. Existing REST API remains unchanged.
WebSocket events are additive and optional for clients.

## 2025-01-14 — Karaoke Feature with Synced Lyrics

### Added
- **Karaoke Generation Pipeline**: Automatic karaoke file creation after audio separation and transcription
  - New `KaraokeProcessor` class in `models.py`
  - Generates LRC format synced lyrics with timestamps
  - Embeds lyrics in MP3 ID3 metadata (USLT tag)
  - Creates dedicated `outputs/Karaoke-pjesme/{file_id}/` storage structure
- **LRC File Generation**: Industry-standard synchronized lyrics format
  - Timestamp format: `[MM:SS.CC]` for each line
  - UTF-8 encoding for multi-language support
  - Includes metadata headers (title, artist, duration)
- **Metadata Embedding**: ID3v2 tags added to karaoke audio
  - USLT (Unsynchronized Lyrics): Full lyrics text
  - TIT2 (Title), TPE1 (Artist), TALB (Album)
- **Enhanced Upload Response**: New `karaoke` object in API response
  - Status, file paths, download URLs
  - Total lines, duration, sync metadata
- **Download Support**: Extended `/download/<file_id>/<track>` endpoint
  - Checks karaoke folder first, then Demucs output
  - Supports downloading LRC, MP3, and JSON sync files
- **Dependencies**: Added `mutagen` library for audio metadata manipulation
- **Testing**: New `test_karaoke.py` script for end-to-end validation
- **Documentation**: Comprehensive `KARAOKE_GUIDE.md` with usage examples

### Changed
- Upload workflow now includes karaoke generation after Demucs + Gemma 3n complete
- Download endpoint checks multiple directories (uploads, outputs, Demucs, karaoke)
- Enhanced error handling for karaoke failures (won't block upload success)

### Technical Details
- **Sync Algorithm**: Uniform time distribution (simple baseline)
  - `time_per_line = total_duration / number_of_lines`
  - Future: Implement forced alignment or AI-powered word-level timing
- **File Formats**:
  - `{file_id}_karaoke.mp3`: Instrumental track with embedded lyrics
  - `{file_id}_karaoke.lrc`: Synced lyrics in LRC format
  - `{file_id}_sync.json`: Complete metadata and timestamps
- **Processing Time**: ~1-3 seconds after separation/transcription
- **Storage**: Minimal overhead (~2KB metadata per file)

### Notes
- Karaoke generation is automatic when `auto_process=true` (default)
- Requires both successful Demucs separation and Gemma 3n transcription
- If either dependency fails, karaoke status will be "failed" but upload succeeds
- LRC files compatible with VLC, karaoke software, and media players
- ID3 metadata readable by most audio players (Windows Media Player, iTunes, etc.)

### Migration
No breaking changes. Existing endpoints and responses remain compatible.
New `karaoke` field added to upload response (optional, only if generated).

## 2025-10-19 — Song List Endpoint & Lion's Roar Studio Integration
- Added `/songs` endpoint to backend, listing uploaded files with processing status and download URL.
- Backend now checks for processed files and exposes download links only for completed jobs.
- Lion's Roar Studio can now filter and display only processed/downloadable songs, improving user experience and error handling.
- Added advanced UI example for song list with download/status/error handling.
- Installed and verified all backend dependencies, checked for version conflicts.
- Added unified processor test utility for backend integration testing.

## 2025-10-19 — Comprehensive Improvement Plan
- Added TODO.md with detailed improvement roadmap covering:
  - Performance and scaling optimizations
  - Security enhancements
  - Code organization and maintainability
  - Testing and quality assurance
  - Error handling and monitoring
  - Feature enhancements
  - DevOps and deployment improvements
  - Documentation
  - Lion's Roar Studio integration
  - Specific technical improvements
- Key priorities identified:
  - Model caching to avoid reloading models on each request
  - Background task queue for long-running operations
  - Refactoring app.py into modular Flask Blueprints
  - Implementing proper authentication system
  - Adding comprehensive API documentation

## 2025-10-17 — Windows build troubleshooting added
- Problem: Running `pip install -r requirements.txt` inside a Windows venv failed with a build error while compiling the `blis` package.
  - Error excerpt: `error: [WinError 2] The system cannot find the file specified` and `ERROR: Failed building wheel for blis`.
- Actions taken:
  - Upgraded packaging tools inside the virtual environment:
    ```powershell
    python -m pip install --upgrade pip setuptools wheel
    ```
  - Installed `blis` via conda as a workaround to avoid building from source on Windows:
    ```powershell
    conda install -c conda-forge blis
    ```
  - Verified `pip`, `setuptools`, and `wheel` were already at newer versions in the venv.
- Notes / Recommendations:
  - On Windows, compiling `blis` requires C build tools (Visual Studio Build Tools or LLVM/clang). If you prefer `pip` installs, install the "C++ build tools" workload from Visual Studio Build Tools before running `pip install -r requirements.txt`.
  - Alternatively, prefer a conda environment for dependencies that include native extensions; `conda install -c conda-forge blis` avoids compilation.

