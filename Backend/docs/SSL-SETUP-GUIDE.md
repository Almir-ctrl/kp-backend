# 🔧 Browser SSL Certificate Setup Guide

## Problem
Your frontend shows `GET https://localhost/health net::ERR_FAILED 200 (OK)` error. This happens because browsers don't trust self-signed SSL certificates by default.

## ✅ Quick Fix (Required for Browser Access)

### Step 1: Accept the Certificate in Your Browser
1. **Open a new browser tab**
2. **Navigate to: `https://localhost`**
3. **You'll see a security warning** (this is normal for self-signed certificates)
4. **Click "Advanced"** (Chrome/Edge) or equivalent in your browser
5. **Click "Proceed to localhost (unsafe)"** or similar option
6. **The page will load** - your browser now trusts the certificate

### Step 2: Verify the AI separator backend is Working
After accepting the certificate, test these URLs:
- **Health Check**: `https://localhost/health`
- **WebSocket**: Your app should now connect to `wss://localhost/transcribe`

## 🔍 Technical Details

### Current Server Status ✅
- **HTTP Server**: `http://localhost` (redirects to HTTPS)
- **HTTPS Server**: `https://localhost` (with self-signed certificate)
- **WebSocket Support**: `wss://localhost/transcribe` (secure WebSocket)
- **Health Endpoint**: `https://localhost/health`

### Certificate Information
- **Type**: Self-signed SSL certificate
- **Validity**: 365 days
- **Domains**: localhost, *.localhost, 127.0.0.1
- **Security**: RSA 4096-bit with SHA256

## 🚀 Production Note
For production deployment, replace self-signed certificates with:
- **Let's Encrypt** (free, automated)
- **Commercial SSL Certificate**
- **Cloud Provider Certificate** (AWS Certificate Manager, etc.)

## 🔄 Regenerate Certificates (If Needed)
```bash
# Windows
.\setup-ssl.bat

# Linux/macOS  
./setup-ssl.sh
```

## 📞 Support
If you still see connection errors after accepting the certificate:
1. Clear browser cache and cookies for localhost
2. Restart your browser completely
3. Try in incognito/private browsing mode
4. Check Windows Firewall or antivirus software

Your AI Music Separator AI separator backend is now ready for secure connections! 🎵🔒