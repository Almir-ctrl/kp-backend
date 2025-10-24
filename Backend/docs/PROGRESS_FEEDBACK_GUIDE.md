# Real-Time Processing Progress Feedback

## Overview

The AI Music Separator backend now provides real-time progress updates during audio processing using WebSocket events. This allows frontends to display live progress bars and status updates as files are being processed.

## Features

- **Real-Time Updates**: WebSocket events emitted at each processing stage
- **Progress Tracking**: Percentage-based progress for each stage
- **Stage-by-Stage Feedback**:
  - Upload (100%)
  - Separation (0-100%)
  - Transcription (0-100%)
  - Karaoke Generation (0-100%)
  - Complete (100%)
- **Error Handling**: Failed stages reported with error messages
- **Non-Blocking**: Progress events don't block HTTP responses

## WebSocket Event Structure

### Event Name
`processing_progress`

### Event Payload

```json
{
  "file_id": "abc123",
  "stage": "separation",
  "progress": 45,
  "message": "Separating audio tracks...",
  "error": null
}
```

**Fields:**
- `file_id` (string): Unique identifier for the uploaded file
- `stage` (string): Current processing stage
  - `upload` - File upload complete
  - `separation` - Audio separation in progress
  - `transcription` - AI transcription in progress
  - `karaoke` - Karaoke generation in progress
  - `complete` - All processing complete
- `progress` (integer): 0-100 percentage
- `message` (string): Human-readable status message
- `error` (string|null): Error message if stage failed (optional)

## Processing Stages

### 1. Upload Complete
```json
{
  "file_id": "abc123",
  "stage": "upload",
  "progress": 100,
  "message": "Upload complete, starting separation..."
}
```

### 2. Separation Starting
```json
{
  "file_id": "abc123",
  "stage": "separation",
  "progress": 10,
  "message": "Separating audio tracks..."
}
```

### 3. Separation Complete
```json
{
  "file_id": "abc123",
  "stage": "separation",
  "progress": 100,
  "message": "Audio separation complete"
}
```

### 4. Transcription Starting
```json
{
  "file_id": "abc123",
  "stage": "transcription",
  "progress": 10,
  "message": "Transcribing lyrics with AI..."
}
```

### 5. Transcription Complete
```json
{
  "file_id": "abc123",
  "stage": "transcription",
  "progress": 100,
  "message": "Transcription complete"
}
```

### 6. Karaoke Starting
```json
{
  "file_id": "abc123",
  "stage": "karaoke",
  "progress": 10,
  "message": "Generating karaoke with synced lyrics..."
}
```

### 7. Karaoke Complete
```json
{
  "file_id": "abc123",
  "stage": "karaoke",
  "progress": 100,
  "message": "Karaoke generation complete"
}
```

### 8. All Processing Complete
```json
{
  "file_id": "abc123",
  "stage": "complete",
  "progress": 100,
  "message": "All processing complete!"
}
```

### Error Example
```json
{
  "file_id": "abc123",
  "stage": "transcription",
  "progress": 100,
  "message": "Transcription failed",
  "error": "Model loading failed: out of memory"
}
```

## Lion's Roar Studio Integration

### JavaScript (Socket.IO)

```javascript
// Connect to backend
const socket = io('http://localhost:5000');

// Listen for progress updates
socket.on('processing_progress', (data) => {
    console.log(`[${data.stage}] ${data.progress}%: ${data.message}`);
    
    // Update UI based on stage
    updateProgressBar(data.stage, data.progress);
    updateStatusMessage(data.stage, data.message);
    
    // Handle errors
    if (data.error) {
        showError(data.stage, data.error);
    }
    
    // Check if complete
    if (data.stage === 'complete') {
        enableDownloadButtons();
    }
});

// Upload file with auto-processing
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_process', 'true');
    
    const response = await fetch('http://localhost:5000/upload?model=demucs', {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    console.log('Upload response:', result);
}
```

### React Example

```jsx
import { useEffect, useState } from 'react';
import io from 'socket.io-client';

function AudioProcessor() {
  const [progress, setProgress] = useState({});
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    const newSocket = io('http://localhost:5000');
    
    newSocket.on('processing_progress', (data) => {
      setProgress(prev => ({
        ...prev,
        [data.stage]: {
          progress: data.progress,
          message: data.message,
          error: data.error
        }
      }));
    });

    setSocket(newSocket);
    
    return () => newSocket.close();
  }, []);

  return (
    <div>
      <ProgressBar stage="upload" data={progress.upload} />
      <ProgressBar stage="separation" data={progress.separation} />
      <ProgressBar stage="transcription" data={progress.transcription} />
      <ProgressBar stage="karaoke" data={progress.karaoke} />
    </div>
  );
}

function ProgressBar({ stage, data = {} }) {
  const { progress = 0, message = 'Waiting...', error } = data;
  
  return (
    <div className={`progress-stage ${error ? 'error' : ''}`}>
      <h4>{stage}</h4>
      <div className="progress-bar">
        <div style={{ width: `${progress}%` }} />
      </div>
      <p>{message}</p>
      {error && <span className="error">{error}</span>}
    </div>
  );
}
```

### Vue Example

```vue
<template>
  <div class="audio-processor">
    <div v-for="stage in stages" :key="stage" class="progress-stage">
      <h4>{{ formatStage(stage) }}</h4>
      <div class="progress-bar">
        <div 
          :style="{ width: `${progress[stage]?.progress || 0}%` }"
          :class="{ error: progress[stage]?.error }"
        />
      </div>
      <p>{{ progress[stage]?.message || 'Waiting...' }}</p>
      <span v-if="progress[stage]?.error" class="error">
        {{ progress[stage].error }}
      </span>
    </div>
  </div>
</template>

<script>
import io from 'socket.io-client';

export default {
  data() {
    return {
      socket: null,
      progress: {},
      stages: ['upload', 'separation', 'transcription', 'karaoke']
    };
  },
  
  mounted() {
    this.socket = io('http://localhost:5000');
    
    this.socket.on('processing_progress', (data) => {
      this.progress = {
        ...this.progress,
        [data.stage]: {
          progress: data.progress,
          message: data.message,
          error: data.error
        }
      };
    });
  },
  
  beforeUnmount() {
    if (this.socket) {
      this.socket.close();
    }
  },
  
  methods: {
    formatStage(stage) {
      return stage.charAt(0).toUpperCase() + stage.slice(1);
    }
  }
};
</script>
```

## Testing

### Using test_progress.html

1. Open `test_progress.html` in your browser
2. Select an audio file (MP3, WAV, etc.)
3. Click "Start Processing"
4. Watch real-time progress updates for each stage
5. Download results when complete

### Manual Testing with curl + Socket.IO client

```bash
# Terminal 1: Start backend
python app.py

# Terminal 2: Listen to WebSocket events (Node.js)
const io = require('socket.io-client');
const socket = io('http://localhost:5000');

socket.on('processing_progress', (data) => {
    console.log(JSON.stringify(data, null, 2));
});

# Terminal 3: Upload file
curl -X POST http://localhost:5000/upload?model=demucs \
  -F "file=@test_audio.mp3" \
  -F "auto_process=true"
```

## Progress Timeline Example

```
[00:00] upload: 100% - Upload complete, starting separation...
[00:01] separation: 10% - Separating audio tracks...
[00:15] separation: 100% - Audio separation complete
[00:16] transcription: 10% - Transcribing lyrics with AI...
[00:45] transcription: 100% - Transcription complete
[00:46] karaoke: 10% - Generating karaoke with synced lyrics...
[00:48] karaoke: 100% - Karaoke generation complete
[00:48] complete: 100% - All processing complete!
```

## UI/UX Recommendations

### Progress Bar Styles

```css
/* Active stage */
.stage.active {
  border-left: 4px solid #667eea;
  animation: pulse 2s infinite;
}

/* Complete stage */
.stage.complete {
  border-left: 4px solid #4caf50;
  opacity: 0.7;
}

/* Error stage */
.stage.error {
  border-left: 4px solid #f44336;
}

/* Progress bar animation */
.progress-fill {
  transition: width 0.5s ease;
  background: linear-gradient(90deg, #667eea, #764ba2);
}
```

### Loading Indicators

- **Spinner**: Show animated spinner for active stage
- **Checkmark**: Display checkmark when stage completes
- **Error Icon**: Show red X if stage fails
- **Percentage**: Display numeric percentage alongside bar

### User Feedback

- Keep completed stages visible (faded)
- Show current stage prominently
- Provide ETA if possible
- Allow cancellation (future feature)
- Show final results with download links

## Performance Considerations

- **WebSocket Overhead**: Minimal (~1KB per event)
- **Event Frequency**: 1-3 events per stage (start, complete)
- **Connection**: Single WebSocket connection per client
- **Scalability**: Socket.IO handles multiple concurrent users

## Error Handling

If a stage fails, the error is included in the progress event:

```javascript
socket.on('processing_progress', (data) => {
    if (data.error) {
        console.error(`${data.stage} failed:`, data.error);
        showNotification(`${data.stage} failed`, 'error');
        // Optionally allow retry
        enableRetryButton(data.stage);
    }
});
```

## Future Enhancements

- **Fine-Grained Progress**: Percentage within each stage (e.g., 0-100% for Demucs)
- **ETA Calculation**: Estimated time remaining based on file size
- **Pause/Resume**: Ability to pause long-running processes
- **Batch Progress**: Track multiple files simultaneously
- **History**: Show progress for past uploads
- **Notifications**: Browser notifications when complete

## Troubleshooting

### Progress Events Not Received

**Check WebSocket Connection:**
```javascript
socket.on('connect', () => console.log('Connected'));
socket.on('disconnect', () => console.log('Disconnected'));
```

**Verify CORS Settings:**
- AI separator backend allows `cors_allowed_origins="*"`
- Check browser console for CORS errors

**Check AI separator backend Logs:**
```bash
# Should see progress emit logs
Auto-processing abc123 with demucs model
Auto-transcribing abc123 with Gemma 3n
Auto-generating karaoke for abc123
```

### Progress Stuck

- AI separator backend might have crashed (check server logs)
- Long-running model operations (Demucs can take 30s+)
- Network issues (check connection status)

### Events Out of Order

- Socket.IO guarantees message order
- If issues persist, use sequence numbers in events

## Resources

- **Socket.IO Client**: https://socket.io/docs/v4/client-api/
- **Flask-SocketIO**: https://flask-socketio.readthedocs.io/
- **test_progress.html**: Interactive demo included in backend

---

**Last Updated**: 2025-10-19  
**Version**: 1.1.0  
**Author**: AI Music Separator Team
