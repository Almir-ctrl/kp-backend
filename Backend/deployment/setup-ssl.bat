@echo off
REM SSL Certificate Setup Script for AI Music Separator Backend (Windows)
REM This script creates self-signed certificates with proper Subject Alternative Names (SAN)

echo 🔐 Setting up SSL certificates for AI Music Separator Backend...

REM Create SSL directory if it doesn't exist
if not exist "nginx\ssl" mkdir "nginx\ssl"

REM Generate improved self-signed certificate with SAN extensions  
docker run --rm -v %cd%/nginx/ssl:/ssl alpine/openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes -keyout /ssl/key.pem -out /ssl/cert.pem -subj "/C=US/ST=Development/L=Local/O=AI Music Separator/OU=Backend/CN=localhost" -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

echo ✅ SSL certificates generated successfully!
echo 📋 Certificate details:
docker run --rm -v %cd%/nginx/ssl:/ssl alpine/openssl x509 -in /ssl/cert.pem -text -noout

echo.
echo 🌐 Server URLs:
echo    HTTP:  http://localhost
echo    HTTPS: https://localhost 
echo    Health: https://localhost/health
echo    WebSocket: wss://localhost/transcribe
echo.
echo ⚠️  BROWSER SETUP REQUIRED:
echo    Since this uses a self-signed certificate, you need to:
echo    1. Visit https://localhost in your browser
echo    2. Click 'Advanced' when you see the security warning
echo    3. Click 'Proceed to localhost (unsafe)'
echo    4. Your browser will now trust the certificate for this session
echo.
echo 🔄 Restarting nginx to load new certificates...
docker-compose restart nginx

echo ✅ Setup complete! Your AI Music Separator Backend is ready.
pause