<!-- Pointer: moved to /part of AI separator backend/README.md -->

See canonical copy at: `/part of AI separator backend/README.md`
> Progress quickstart moved to the part of AI separator backend overview.

Canonical location:

- /part of AI separator backend/README.md
# Quick Reference: Progress Feedback

## ✅ Feature Complete

Real-time loading indicators and progress bars now available for all audio processing stages.

## How to Use

### Open Demo
```
1. Open test_progress.html in your browser
2. Select or drag an audio file
3. Click "Start Processing"
4. Watch real-time progress updates
```

### Integrate in Your App

```javascript
// 1. Connect to WebSocket
const socket = io('http://localhost:5000');

// 2. Listen for progress
socket.on('processing_progress', (data) => {
    console.log(`${data.stage}: ${data.progress}%`);
    updateProgressBar(data.stage, data.progress);
    showMessage(data.message);
});

// 3. Upload file (progress events will fire automatically)
const formData = new FormData();
formData.append('file', audioFile);
formData.append('auto_process', 'true');

fetch('http://localhost:5000/upload?model=demucs', {
    method: 'POST',
    body: formData
});
```

## Progress Stages

| Stage | Duration | Description |
|-------|----------|-------------|
| 📤 **Upload** | Instant | File uploaded to server |
| 🎼 **Separation** | 15-30s | Demucs splits audio (vocals + instrumental) |
| 📝 **Transcription** | 20-40s | Gemma 3n transcribes lyrics |
| 🎤 **Karaoke** | 2-5s | Generates synced lyrics + LRC file |
| ✅ **Complete** | - | All processing done! |

## Event Structure

```json
{
  "file_id": "abc123",
  "stage": "separation",
  "progress": 75,
  "message": "Separating audio tracks..."
}
```

## Visual States

```
⏳ Waiting       - Gray, 0%
🔄 Processing    - Blue, 1-99%, animated spinner
✓ Complete      - Green, 100%, checkmark
❌ Error        - Red, stopped, error message
```

## Features

✅ Real-time WebSocket updates  
✅ Stage-by-stage progress tracking  
✅ Animated progress bars  
✅ Error reporting  
✅ Connection status indicator  
✅ Beautiful demo UI  
✅ Download links when complete  

## Server Status

🟢 **Running**: http://localhost:5000  
🟢 **WebSocket**: ws://localhost:5000  
🟢 **Demo**: test_progress.html  

## Files

- **Demo**: `test_progress.html` (interactive UI)
- **Guide**: `PROGRESS_FEEDBACK_GUIDE.md` (full docs)
- **Summary**: `PROGRESS_IMPLEMENTATION_SUMMARY.md` (technical details)
- **Code**: `app.py` (progress events)

## Example Timeline

```
[0s]  📤 Upload: 100% - Upload complete
[1s]  🎼 Separation: 10% - Starting...
[15s] 🎼 Separation: 100% - Complete
[16s] 📝 Transcription: 10% - Starting...
[45s] 📝 Transcription: 100% - Complete
[46s] 🎤 Karaoke: 10% - Starting...
[48s] 🎤 Karaoke: 100% - Complete
[48s] ✅ Complete: 100% - All done!
```

## Troubleshooting

**No progress updates?**
- Check WebSocket connection (see status indicator)
- Verify backend is running on port 5000
- Check browser console for errors

**Progress stuck?**
- Normal for long files (Demucs can take 30s+)
- Check backend logs for errors
- Refresh page and try again

## Next Steps

1. ✅ Try the demo: `test_progress.html`
2. 📖 Read the guide: `PROGRESS_FEEDBACK_GUIDE.md`
3. 🔧 Integrate in your frontend (see examples above)
4. 🎨 Customize UI to match your design

---

**Ready to use!** Just open `test_progress.html` and start uploading.
