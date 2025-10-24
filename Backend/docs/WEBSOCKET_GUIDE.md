# WebSocket Support for Real-Time Transcription

## Overview

Your AI Music Separator AI separator backend now includes **WebSocket support** for real-time audio transcription using OpenAI Whisper. This enables secure WebSocket connections (WSS) over HTTPS, solving the Mixed Content security error.

## What's New

### ✅ WebSocket Support Added
- **Real-time transcription** via WebSocket connections
- **Secure connections** (WSS) over HTTPS 
- **Flask-SocketIO** integration for reliable WebSocket handling
- **nginx proxy** configured for WebSocket upgrades

### ✅ Mixed Content Issue Fixed
The error you encountered:
```
Mixed Content: The page at 'https://aistudio.google.com/' was loaded over HTTPS, 
but attempted to connect to the insecure WebSocket endpoint 'ws://172.18.0.2:8000/transcribe'
```

Is now **resolved** because:
- WebSocket connections use secure **WSS protocol**
- nginx handles SSL termination and WebSocket upgrades
- All connections are now HTTPS-compatible

## WebSocket Endpoint

### Connection URL
```javascript
// For browsers (from HTTPS pages)
wss://localhost/socket.io/

// With namespace for transcription
wss://localhost/socket.io/?EIO=4&transport=websocket
```

### Namespace
```
/transcribe
```

## Client Implementation

### JavaScript Example (Socket.IO Client)
```javascript
// Include Socket.IO client library
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>

// Connect to WebSocket
const socket = io('wss://localhost/transcribe', {
    transports: ['websocket', 'polling'],
    rejectUnauthorized: false // For self-signed certificates
});

// Event handlers
socket.on('connect', () => {
    console.log('Connected to transcription service');
});

socket.on('transcription', (data) => {
    console.log('Transcription:', data.transcription);
});

socket.on('error', (data) => {
    console.error('Error:', data.message);
});

// Send audio data
socket.emit('audio', {
    payload: {
        data: base64AudioData,
        mimeType: 'audio/pcm;rate=16000'
    }
});

// Finish transcription
socket.emit('finish');
```

## WebSocket Events

### Client → Server

#### `audio`
Send audio chunks for transcription.

**Payload:**
```javascript
{
    payload: {
        data: "base64-encoded-audio-data",
        mimeType: "audio/pcm;rate=16000"
    }
}
```

**Audio Format Requirements:**
- **Sample Rate:** 16kHz
- **Format:** 16-bit PCM
- **Encoding:** Base64
- **Minimum Length:** 1 second (16,000 samples)

#### `finish`
Signal end of transcription session.

**Payload:** None

### Server → Client

#### `connected`
Confirmation of successful connection.

**Response:**
```javascript
{
    message: "Connected to transcription service"
}
```

#### `transcription`
Real-time transcription results.

**Response:**
```javascript
{
    transcription: "transcribed text here"
}
```

#### `error`
Error messages during transcription.

**Response:**
```javascript
{
    message: "error description"
}
```

#### `finished`
Transcription session completed.

**Response:**
```javascript
{
    message: "Transcription completed"
}
```

## Testing WebSocket Connection

### 1. Health Check
Test if WebSocket support is enabled:
```bash
curl -k https://localhost/health
```

Expected response:
```json
{
    "status": "healthy",
    "message": "AI Model AI separator backend with WebSocket support is running",
    "websocket_support": true,
    "transcription_endpoint": "/transcribe"
}
```

### 2. Browser Test
Open `websocket-test.html` in your browser to test the connection:
```bash
# Navigate to the project directory and open the test file
start websocket-test.html  # Windows
open websocket-test.html   # macOS
```

### 3. Direct WebSocket Test (Python)
```python
import socketio
import base64
import numpy as np

# Create SocketIO client
sio = socketio.Client(ssl_verify=False)

@sio.event
def connect():
    print('Connected to transcription service')

@sio.event
def transcription(data):
    print(f'Transcription: {data["transcription"]}')

@sio.event
def error(data):
    print(f'Error: {data["message"]}')

# Connect to server
sio.connect('https://localhost', namespaces=['/transcribe'])

# Send test audio (silence)
audio_data = np.zeros(16000, dtype=np.int16)  # 1 second of silence
encoded_data = base64.b64encode(audio_data.tobytes()).decode()

sio.emit('audio', {
    'payload': {
        'data': encoded_data,
        'mimeType': 'audio/pcm;rate=16000'
    }
}, namespace='/transcribe')

# Finish
sio.emit('finish', namespace='/transcribe')
sio.disconnect()
```

## Production Deployment

### Docker Compose
Your existing setup is already configured for WebSocket support:

```bash
# Start services with WebSocket support
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs ai-backend
```

### nginx Configuration
The nginx configuration includes WebSocket proxy support:

```nginx
# WebSocket endpoints for real-time transcription
location /socket.io/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket specific timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # Disable buffering for real-time communication
    proxy_buffering off;
}
```

## Troubleshooting

### Common Issues

#### 1. Mixed Content Error
**Symptom:** Browser blocks WSS connection from HTTPS page
**Solution:** ✅ **Fixed** - AI separator backend now supports secure WebSocket (WSS)

#### 2. Connection Refused
**Symptom:** Cannot connect to WebSocket
**Check:**
```bash
# Verify containers are running
docker-compose ps

# Check backend logs
docker-compose logs ai-backend

# Test HTTPS endpoint
curl -k https://localhost/health
```

#### 3. Self-Signed Certificate Warning
**Symptom:** Browser shows security warning
**Solution:** 
- Click "Advanced" → "Proceed to localhost (unsafe)"
- Or use `rejectUnauthorized: false` in client code

#### 4. Audio Format Issues
**Symptom:** No transcription results
**Check:**
- Audio sample rate is 16kHz
- Audio is 16-bit PCM format
- Minimum 1 second of audio data
- Base64 encoding is correct

### Debug Mode
Enable debug logging:
```bash
# Set debug environment variable
echo "DEBUG=true" >> .env

# Restart containers
docker-compose restart ai-backend
```

## Performance Notes

- **Whisper Model:** Uses 'base' model by default for speed
- **Audio Processing:** Processes chunks in real-time
- **Memory Usage:** Model loads on first request (~400MB)
- **Concurrent Connections:** Supports multiple simultaneous clients

## Security Considerations

- **HTTPS Only:** All connections use SSL/TLS encryption
- **CORS Configured:** Cross-origin requests properly handled  
- **Self-Signed Certificates:** For development (use proper certificates in production)
- **Rate Limiting:** Consider implementing for production use

Your backend is now fully compatible with HTTPS-based frontend applications and supports secure real-time audio transcription! 🎉