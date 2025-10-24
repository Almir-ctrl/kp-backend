# Docker Deployment Guide - AI Music Separator Backend

## Prerequisites

- Docker 20.10+ with GPU support
- NVIDIA Container Toolkit installed
- NVIDIA GPU with CUDA support (tested with RTX 5070 Ti, sm_120)
- Docker Compose v2+

## GPU Support Setup

### 1. Install NVIDIA Container Toolkit

**Ubuntu/Debian:**
```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**Windows with WSL2:**
```powershell
# Ensure WSL2 with CUDA support is enabled
# Install Docker Desktop for Windows with WSL2 backend
# GPU support is automatically enabled
```

### 2. Verify GPU Access

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

Should show your GPU (e.g., RTX 5070 Ti).

## Quick Start

### Development Mode (Port 5000)

```bash
# Build and start with GPU support
docker-compose -f docker-compose.dev.yml up --build

# Or run in detached mode
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f ai-backend

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Production Mode (Port 8000 with Nginx)

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Configuration

### Environment Variables

Create `.env` file in project root:

```env
# Flask settings
DEBUG=False
SECRET_KEY=your-secure-secret-key-here

# Server settings
PORT=8000
WORKERS=2
WORKER_CLASS=eventlet

# CORS
CORS_ORIGINS=*

# GPU settings (auto-detected)
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### Volume Mounts

- `./uploads:/app/uploads` - Uploaded audio files
- `./outputs:/app/outputs` - Processed outputs (stems, transcriptions, karaoke)
- `ai_models:/root/.cache` - AI model cache (persistent)

## GPU Configuration

### PyTorch Nightly (sm_120 Support)

The Dockerfile automatically installs PyTorch Nightly with CUDA 12.4 support, which includes:
- Support for RTX 5070 Ti (sm_120 compute capability)
- GPU-accelerated Demucs audio separation
- GPU-accelerated Whisper transcription
- All AI models run on GPU by default

### Memory Requirements

**Minimum:**
- 6GB GPU VRAM
- 6GB System RAM

**Recommended:**
- 12GB+ GPU VRAM (for large models)
- 12GB+ System RAM
- 6 CPU cores

## Testing GPU Inside Container

```bash
# Enter running container
docker exec -it <container_id> bash

# Test PyTorch GPU
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"

# Expected output:
# CUDA: True
# GPU: NVIDIA GeForce RTX 5070 Ti
```

## API Endpoints

Once running, the backend exposes:

- `GET /health` - Health check
- `POST /upload` - Upload and auto-process audio
- `POST /process/<model>/<file_id>` - Process with specific model
- `GET /karaoke/songs` - List karaoke songs
- `GET /download/<file_id>` - Download processed files

Full API documentation: See `API_ENDPOINTS.md`

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA runtime is available
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Check container can see GPU
docker-compose -f docker-compose.dev.yml exec ai-backend nvidia-smi

# Verify PyTorch sees GPU
docker-compose -f docker-compose.dev.yml exec ai-backend python -c "import torch; print(torch.cuda.is_available())"
```

### Out of Memory Errors

Reduce memory usage in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 8G  # Reduce from 12G
```

Or use smaller model variants:
- Demucs: `htdemucs` instead of `htdemucs_ft`
- Whisper: `medium` instead of `large`

### PyTorch Version Issues

If you see "CUDA capability sm_120 is not compatible":

1. Ensure Dockerfile installs PyTorch Nightly:
   ```dockerfile
   RUN pip install --pre torch torchvision torchaudio \
       --index-url https://download.pytorch.org/whl/nightly/cu124
   ```

2. Rebuild image:
   ```bash
   docker-compose build --no-cache
   ```

## Performance Optimization

### Use GPU for All Models

The backend automatically detects GPU and uses it for:
- ✅ Demucs audio separation
- ✅ Whisper transcription
- ✅ Pitch analysis

### Multi-GPU Setup

To use specific GPU:

```yaml
environment:
  - NVIDIA_VISIBLE_DEVICES=0  # Use first GPU only
```

### CPU Fallback

If GPU is unavailable, models automatically fall back to CPU (slower).

## Production Deployment

### SSL/HTTPS Setup

1. Place SSL certificates in `nginx/ssl/`:
   - `cert.pem`
   - `key.pem`

2. Update `nginx/nginx-production.conf`

3. Start with production compose:
   ```bash
   docker-compose up -d
   ```

### Health Monitoring

```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "available_models": ["demucs", "whisper", "musicgen", "pitch_analysis", "gemma_3n", "karaoke"],
  "websocket_support": true
}
```

### Log Management

Logs are stored in `logs/` directory:
- `app.log` - Formatted logs
- `app.json.log` - JSON structured logs

Rotate logs to prevent disk fill:
```bash
# Add to cron
0 0 * * * find /app/logs -name "*.log*" -mtime +7 -delete
```

## Backup & Restore

### Backup Data

```bash
# Backup uploads and outputs
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ outputs/

# Backup AI model cache
docker run --rm -v ai_models:/data -v $(pwd):/backup ubuntu tar czf /backup/models-cache.tar.gz /data
```

### Restore Data

```bash
# Restore uploads/outputs
tar -xzf backup-20251021.tar.gz

# Restore model cache
docker run --rm -v ai_models:/data -v $(pwd):/backup ubuntu tar xzf /backup/models-cache.tar.gz -C /
```

## Updates

```bash
# Pull latest code
git pull

# Rebuild and restart (comment out watch: section if present)
docker compose -f docker-compose.dev.yml build --no-cache
docker compose -f docker-compose.dev.yml up -d
```

## Support

For issues specific to:
- **GPU support**: Check NVIDIA Container Toolkit installation
- **PyTorch errors**: Ensure PyTorch Nightly (torch, torchvision) for CUDA 13.0 is installed
- **transformers errors**: Ensure transformers >=4.39.0 is installed in requirements for Gemma2/Gemma3N support
- **API errors**: Check `logs/app.log` for detailed error messages
- **Karaoke no lyrics**: Ensure Whisper transcription completed successfully

See `COMPREHENSIVE_TESTING_REPORT.md` for detailed troubleshooting.
