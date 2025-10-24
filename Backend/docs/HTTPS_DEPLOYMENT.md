# HTTPS Docker Deployment Guide

## 🔐 HTTPS Setup Complete!

Your AI backend now runs with **HTTPS support** using nginx reverse proxy and SSL certificates.

## 🌐 **Available Endpoints:**

- **HTTPS (Secure)**: `https://localhost`
- **HTTP**: Redirects to HTTPS automatically
- **API Base**: `https://localhost/`

## 🚀 **Quick Start:**

### 1. Generate SSL Certificates (First time only)

**Windows:**
```powershell
.\generate-ssl.bat
```

**Linux/Mac:**
```bash
./generate-ssl.sh
```

**Or use Docker (Cross-platform):**
```bash
docker run --rm -v "${PWD}/nginx/ssl:/certs" alpine/openssl req -x509 -newkey rsa:2048 -keyout /certs/key.pem -out /certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Development/CN=localhost"
```

### 2. Start HTTPS Services

```bash
docker-compose up -d
```

### 3. Test HTTPS Endpoints

```bash
# Health check
curl -k https://localhost/health

# List available models  
curl -k https://localhost/models

# PowerShell (Windows)
(Invoke-WebRequest -Uri "https://localhost/health" -SkipCertificateCheck).Content
```

## 🔧 **Architecture:**

```
Browser/Client
     ↓ HTTPS (443)
   Nginx Reverse Proxy
     ↓ HTTP (8000)
   AI AI separator backend (Flask)
```

**Benefits:**
- ✅ **Secure HTTPS** communication
- ✅ **Browser compatibility** (no mixed content issues)
- ✅ **Load balancing** ready
- ✅ **SSL termination** at nginx
- ✅ **Security headers** included
- ✅ **CORS** properly configured

## 📋 **API Usage Examples:**

### Upload Files (HTTPS)
```bash
# Upload for Demucs
curl -k -X POST -F "file=@song.mp3" https://localhost/upload/demucs

# Upload for Whisper
curl -k -X POST -F "file=@speech.wav" https://localhost/upload/whisper
```

### Process Files (HTTPS)
```bash
# Process with Demucs
curl -k -X POST https://localhost/process/demucs/your-file-id

# Process with Whisper
curl -k -X POST https://localhost/process/whisper/your-file-id
```

### PowerShell Examples
```powershell
# Upload file
$response = Invoke-WebRequest -Uri "https://localhost/upload/whisper" -Method Post -Form @{file = Get-Item "speech.wav"} -SkipCertificateCheck
$result = $response.Content | ConvertFrom-Json

# Process file
$processResponse = Invoke-WebRequest -Uri "https://localhost/process/whisper/$($result.file_id)" -Method Post -SkipCertificateCheck
```

## 🌍 **Production Deployment:**

For production with real domain and Let's Encrypt SSL:

### 1. Use Production Compose File
```bash
cp docker-compose.prod.yml docker-compose.yml
```

### 2. Update Environment
```bash
# Edit .env file
SECRET_KEY=your-super-secret-production-key
DOMAIN=yourdomain.com
EMAIL=your-email@example.com
```

### 3. Deploy with Let's Encrypt
```bash
docker-compose up -d
```

## 🔒 **Security Features:**

- **TLS 1.2/1.3** encryption
- **HSTS** headers (Strict Transport Security)
- **XSS Protection** headers
- **Content Type** protection
- **Frame Options** (clickjacking protection)
- **CORS** properly configured
- **File upload** size limits (100MB)

## ⚠️ **Development Certificate Warning:**

The self-signed certificate will show a browser warning:
1. Click **"Advanced"**
2. Click **"Proceed to localhost (unsafe)"**
3. Your browser will remember this choice

For production, use a real SSL certificate from Let's Encrypt or a CA.

## 🐳 **Container Management:**

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## 📊 **Monitoring:**

```bash
# Check container status
docker-compose ps

# View nginx logs
docker-compose logs nginx

# View backend logs  
docker-compose logs ai-backend
```

Your multi-model AI backend is now **production-ready with HTTPS**! 🚀🔐