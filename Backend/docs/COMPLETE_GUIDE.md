# 🎵 AI Music Separator Backend - Complete Setup Guide

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Multi-Model Support](#multi-model-support)
- [WebSocket Real-Time Transcription](#websocket-real-time-transcription)
- [HTTPS Deployment](#https-deployment)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

---

## 🎯 Overview

A comprehensive Flask-based backend server supporting multiple AI models for audio processing:

- **Demucs**: Audio source separation (vocals, drums, bass, other)
- **Whisper**: Real-time speech-to-text transcription via WebSocket
- **MusicGen**: Text-to-music generation (framework ready)

### ✅ Key Features
- **HTTPS Support** with nginx reverse proxy
- **WebSocket (WSS)** for real-time transcription
- **Docker Containerization** for easy deployment
- **Multi-format support** (MP3, WAV, FLAC, M4A, OGG)
- **RESTful API** with CORS support
- **Production ready** with SSL certificates

---

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Required
- Docker & Docker Compose
- 4GB+ RAM (for AI models)
- 10GB+ storage space
```

### 2. Generate SSL Certificates (First time only)

**Windows:**
```powershell
.\generate-ssl.bat
```

**Linux/Mac:**
```bash
./generate-ssl.sh
```

### 3. Start Services
```bash
# Start all services with HTTPS
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f ai-backend
```

### 4. Test Installation
```bash
# Health check (HTTPS)
curl -k https://localhost/health

# List available models
curl -k https://localhost/models

# PowerShell (Windows)
(Invoke-WebRequest -Uri "https://localhost/health" -SkipCertificateCheck).Content
```

**Expected Response:**
```json
{
  "status": "healthy",
  "message": "AI Model Backend with WebSocket support is running",
  "available_models": ["demucs", "whisper", "musicgen"],
  "websocket_support": true,
  "transcription_endpoint": "/transcribe"
}
```

---

## 🤖 Multi-Model Support

### Model Configuration
```python
# Available models (config.py)
MODELS = {
    'demucs': {
        'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'},
        'purpose': 'Audio source separation'
    },
    'whisper': {
        'file_types': {'mp3', 'wav', 'flac', 'm4a', 'ogg'},
        'purpose': 'Speech-to-text transcription'
    },
    'musicgen': {
        'file_types': {'txt'},
        'purpose': 'Text-to-music generation'
    }
}
```

### 1. Demucs (Audio Separation)

**Upload & Process:**
```bash
# Upload audio file
curl -X POST -F "file=@song.mp3" https://localhost/upload

# Response: {"file_id": "abc123..."}

# Process with Demucs
curl -k -X POST https://localhost/process/demucs/abc123

# Check status
curl -k https://localhost/status/abc123

# Download separated tracks
curl -k https://localhost/download/abc123/vocals -o vocals.wav
curl -k https://localhost/download/abc123/drums -o drums.wav
curl -k https://localhost/download/abc123/bass -o bass.wav  
curl -k https://localhost/download/abc123/other -o other.wav
```

**Model Variants:**
```bash
# Use specific Demucs model
curl -k -X POST -H "Content-Type: application/json" \
  -d '{"model_variant": "mdx_extra"}' \
  https://localhost/process/demucs/abc123
```

### 2. Whisper (Speech-to-Text)

**File-based Transcription:**
```bash
# Upload audio file
curl -k -X POST -F "file=@speech.wav" https://localhost/upload

# Process with Whisper  
curl -k -X POST https://localhost/process/whisper/abc123

# Download transcription
curl -k https://localhost/download/abc123/transcription -o transcript.txt
```

**Real-time WebSocket Transcription:**
See [WebSocket section](#websocket-real-time-transcription) below.

---

## 🔌 WebSocket Real-Time Transcription

### ✅ Mixed Content Issue FIXED
The backend now supports **secure WebSocket (WSS)** connections, resolving browser Mixed Content errors when connecting from HTTPS pages.

### Connection Setup

**JavaScript (Socket.IO Client):**
```javascript
// Include Socket.IO client
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
    console.log('Real-time transcription:', data.transcription);
});

socket.on('error', (data) => {
    console.error('Error:', data.message);
});

// Send audio data (16kHz PCM, Base64 encoded)
socket.emit('audio', {
    payload: {
        data: base64AudioData,
        mimeType: 'audio/pcm;rate=16000'
    }
});

// Finish transcription
socket.emit('finish');
```

### WebSocket Events

| Event | Direction | Description | Payload |
|-------|-----------|-------------|---------|
| `connect` | Server→Client | Connection established | `{message: "Connected to transcription service"}` |
| `audio` | Client→Server | Send audio chunk | `{payload: {data: "base64", mimeType: "audio/pcm;rate=16000"}}` |
| `transcription` | Server→Client | Real-time results | `{transcription: "text"}` |
| `finish` | Client→Server | End session | None |
| `error` | Server→Client | Error occurred | `{message: "error description"}` |

### Audio Format Requirements
- **Sample Rate:** 16kHz  
- **Format:** 16-bit PCM
- **Encoding:** Base64
- **Minimum Length:** 1 second (16,000 samples)

---

## 🔐 HTTPS Deployment

### SSL Certificate Generation

**Self-Signed (Development):**
```bash
# Windows
.\generate-ssl.bat

# Linux/Mac  
./generate-ssl.sh

# Docker (Cross-platform)
docker run --rm -v "${PWD}/nginx/ssl:/certs" alpine/openssl req -x509 -newkey rsa:2048 -keyout /certs/key.pem -out /certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Development/CN=localhost"
```

**Production (Let's Encrypt):**
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy to nginx directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./nginx/ssl/key.pem
```

### nginx Configuration Highlights

```nginx
# nginx/nginx.conf
server {
    listen 443 ssl;
    http2 on;
    server_name localhost;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # WebSocket support for /socket.io/
    location /socket.io/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
    }
    
    # API endpoints
    location / {
        proxy_pass http://backend;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Access-Control-Allow-Origin * always;
    }
}
```

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description | Body/Params |
|--------|----------|-------------|-------------|
| `GET` | `/health` | Health check | None |
| `GET` | `/models` | List available models | None |
| `POST` | `/upload` | Upload file | `multipart/form-data` |
| `POST` | `/process/<model>/<file_id>` | Process with AI model | JSON: `{model_variant: "..."}` |
| `GET` | `/status/<file_id>` | Check processing status | None |
| `GET` | `/download/<file_id>/<track>` | Download result | None |
| `GET` | `/files/<file_id>` | List available files | None |
| `DELETE` | `/cleanup/<file_id>` | Delete files | None |

### Legacy Endpoints (Backward Compatibility)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/separate/<file_id>` | Demucs separation (legacy) |

### WebSocket Namespace

| Endpoint | Description |
|----------|-------------|
| `wss://localhost/transcribe` | Real-time transcription |

---

## ⚙️ Configuration

### Environment Variables
```bash
# .env file
DEBUG=False
SECRET_KEY=your-secret-key-change-in-production
PORT=8000
CORS_ORIGINS=*
DEMUCS_MODEL=htdemucs
WHISPER_MODEL=base
```

### Docker Compose Configuration
```yaml
# docker-compose.yml
services:
  ai-backend:
    build:
      context: .
      dockerfile: Dockerfile.simple
    environment:
      - DEBUG=False
      - SECRET_KEY=your-secret-key-here-change-this
      - PORT=8000
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
      - ai_models:/root/.cache
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
```

### Model Configuration
```python
# config.py
class Config:
    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a', 'ogg', 'txt'}
    
    # Model settings
    DEMUCS_MODEL = 'htdemucs'  # or 'mdx', 'mdx_extra', etc.
    WHISPER_MODEL = 'base'     # tiny, base, small, medium, large
    
    # Directories
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Mixed Content Error (FIXED ✅)
**Symptom:** `Mixed Content: ... attempted to connect to insecure WebSocket`  
**Solution:** ✅ AI separator backend now supports secure WebSocket (WSS) over HTTPS

#### 2. Container Restart Loop
```bash
# Check logs
docker-compose logs ai-backend

# Common causes:
# - Missing dependencies
# - Memory limitations  
# - Port conflicts
```

#### 3. SSL Certificate Issues
```bash
# Regenerate certificates
rm -rf nginx/ssl/*
./generate-ssl.sh

# Or use Docker method
docker run --rm -v "${PWD}/nginx/ssl:/certs" alpine/openssl req -x509 -newkey rsa:2048 -keyout /certs/key.pem -out /certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Development/CN=localhost"
```

#### 4. Model Download Issues
```bash
# Clear model cache
docker-compose down
docker volume rm aimusicseparator-backend_ai_models
docker-compose up -d
```

#### 5. WebSocket Connection Refused
```bash
# Verify nginx WebSocket proxy
docker-compose logs nginx

# Test direct backend connection
curl -k https://localhost/health

# Check WebSocket support in response
```

### Debug Mode
```bash
# Enable debug logging
echo "DEBUG=true" >> .env
docker-compose restart ai-backend

# View real-time logs
docker-compose logs -f ai-backend
```

### Performance Tuning
```yaml
# Increase memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G    # Increase for larger models
    reservations:
      memory: 4G
```

---

## 🏭 Production Deployment

### Checklist
- [ ] Use proper SSL certificates (Let's Encrypt)
- [ ] Change default `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up monitoring and logging
- [ ] Configure automatic backups
- [ ] Implement rate limiting
- [ ] Set up health checks

### Security Recommendations
```nginx
# Additional security headers
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

### Monitoring
```bash
# Health check endpoint for monitoring
curl -k https://localhost/health

# Expected response time: < 2 seconds
# Expected uptime: > 99.9%
```

### Backup Strategy
```bash
# Backup volumes
docker run --rm -v aimusicseparator-backend_ai_models:/data -v $(pwd):/backup alpine tar czf /backup/ai_models_backup.tar.gz /data

# Backup configuration
tar czf config_backup.tar.gz docker-compose.yml nginx/ .env
```

---

## 📞 Support

### File Structure
```
AiMusicSeparator-AI separator backend/
├── app.py                    # Main Flask application with WebSocket
├── config.py                 # Configuration settings
├── models.py                 # AI model processors
├── production.py             # Production server launcher
├── docker-compose.yml        # Docker services configuration
├── Dockerfile.simple         # Container build instructions
├── requirements.txt          # Python dependencies (dev)
├── requirements-prod.txt     # Python dependencies (production)
├── nginx/
│   ├── nginx.conf           # nginx reverse proxy config
│   └── ssl/                 # SSL certificates
├── uploads/                 # Uploaded files
├── outputs/                 # Processed results
└── websocket-test.html      # WebSocket connection test
```

### Key Files
- **`app.py`**: Main application with WebSocket support
- **`docker-compose.yml`**: Complete HTTPS deployment configuration
- **`nginx/nginx.conf`**: WebSocket-enabled reverse proxy
- **`config.py`**: Multi-model configuration
- **`websocket-test.html`**: Test WebSocket connections

### Quick Commands Reference
```bash
# Full deployment
docker-compose up -d

# Check health
curl -k https://localhost/health

# View logs
docker-compose logs -f ai-backend

# Stop services
docker-compose down

# Rebuild
docker-compose up -d --build

# Clean up
docker system prune -a
```

---

**🎉 Your AI Music Separator AI separator backend is now ready for production with full HTTPS and WebSocket support!**

The system supports:
- ✅ **Secure HTTPS** connections
- ✅ **WebSocket (WSS)** real-time transcription  
- ✅ **Multi-model AI** processing (Demucs, Whisper)
- ✅ **Docker containerization**
- ✅ **Production-ready** configuration
- ✅ **Browser compatibility** (no Mixed Content errors)