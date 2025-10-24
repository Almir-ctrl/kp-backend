<!-- Pointer: moved to /part of AI separator backend/whisperer/README.md -->

See canonical copy at: `/part of AI separator backend/whisperer/README.md`
# Quick Start: Karaoke Feature

## ✅ Feature Complete & Operational

The backend now automatically generates karaoke files with synced lyrics and embedded metadata when you upload audio files.

## How to Use

### 1. Upload Audio File
```bash
# Using curl
curl -X POST http://localhost:5000/upload?model=demucs \
  -F "file=@your_song.mp3" \
  -F "auto_process=true"

# Using test_upload.html
# Open in browser, select file, click upload
```

### 2. AI separator backend Auto-Processing
The system automatically:
1. ✅ Separates audio into vocals + instrumental (Demucs 2-stem)
2. ✅ Transcribes lyrics with AI (Gemma 3n)
3. ✅ **Generates karaoke package** (NEW!)
   - Synced LRC lyrics file
   - Instrumental MP3 with embedded lyrics metadata
   - Complete JSON sync data

### 3. Get Karaoke Files
```bash
# Download karaoke audio (instrumental + metadata)
http://localhost:5000/download/{file_id}/{file_id}_karaoke.mp3

# Download synced lyrics (LRC format)
http://localhost:5000/download/{file_id}/{file_id}_karaoke.lrc

# Download sync metadata (JSON)
http://localhost:5000/download/{file_id}/{file_id}_sync.json
```

## Response Example

```json
{
  "file_id": "abc123",
  "status": "completed",
  "karaoke": {
    "status": "completed",
    "karaoke_dir": "outputs/Karaoke-pjesme/abc123",
    "lrc_file": "outputs/Karaoke-pjesme/abc123/abc123_karaoke.lrc",
    "audio_file": "outputs/Karaoke-pjesme/abc123/abc123_karaoke.mp3",
    "total_lines": 42,
    "duration": 180.5,
    "download_url": "/download/abc123/abc123_karaoke.mp3"
  }
}
```

## Test It

```powershell
# Run test script
python test_karaoke.py

# Server running on:
# http://127.0.0.1:5000
# http://192.168.0.13:5000
```

## What You Get

### 📁 Karaoke Package in `outputs/Karaoke-pjesme/{file_id}/`
1. **{file_id}_karaoke.mp3** - Instrumental track with embedded lyrics
2. **{file_id}_karaoke.lrc** - Synced lyrics with timestamps
3. **{file_id}_sync.json** - Complete metadata

### 🎤 LRC Format (Synced Lyrics)
```lrc
[ti:Karaoke Song]
[ar:Unknown Artist]
[al:]
[length:03:00]

[00:00.50]First line of lyrics
[00:05.20]Second line of lyrics
[00:10.80]Third line continues here
```

### 🎵 Embedded Metadata (ID3 Tags)
- **USLT**: Full lyrics text
- **TIT2**: Title
- **TPE1**: Artist
- **TALB**: Album

## Play Karaoke

### VLC Media Player
1. Open karaoke.mp3
2. Place .lrc file in same folder
3. Lyrics display automatically

### Windows Media Player
- Reads embedded lyrics from ID3 tags
- Shows full text (non-synced)

### Karaoke Software
- Import .lrc file directly
- Standard format compatible with all karaoke apps

## Documentation

📖 **Full Guide (canonical)**: `/part of AI separator backend/whisperer/WHISPER_KARAOKE_FIX.md`
📝 **Changelog**: `server/CHANGELOG.md`
✅ **TODO**: Marked complete in `TODO.md`
📊 **Summary**: `KARAOKE_IMPLEMENTATION_SUMMARY.md`

## Status

✅ **Server Running**: http://localhost:5000  
✅ **Dependencies Installed**: mutagen  
✅ **Tests Available**: test_karaoke.py  
✅ **Ready to Use**: YES

---

**Need Help?** Check `/part of AI separator backend/whisperer/WHISPER_KARAOKE_FIX.md` for troubleshooting and advanced usage.

> This file is an archive pointer. The canonical karaoke docs live under `/part of AI separator backend/whisperer/`.
