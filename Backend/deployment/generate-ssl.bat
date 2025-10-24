@echo off
REM Generate self-signed SSL certificate for development (Windows)

echo 🔐 Generating SSL certificate for HTTPS...

REM Create SSL directory if it doesn't exist  
if not exist nginx\ssl mkdir nginx\ssl

REM Check if OpenSSL is available
where openssl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ OpenSSL not found. Please install OpenSSL or use Docker method.
    echo.
    echo Alternative: Use Docker to generate certificates:
    echo docker run --rm -v %cd%/nginx/ssl:/certs alpine/openssl req -x509 -newkey rsa:2048 -keyout /certs/key.pem -out /certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    pause
    exit /b 1
)

REM Generate private key
openssl genrsa -out nginx/ssl/key.pem 2048

REM Generate self-signed certificate
openssl req -x509 -new -key nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

echo ✅ SSL certificate generated!
echo 📄 Certificate: nginx\ssl\cert.pem
echo 🔑 Private key: nginx\ssl\key.pem
echo.
echo ⚠️  This is a self-signed certificate for development only.
echo    Browsers will show a security warning - click 'Advanced' ^> 'Proceed to localhost'
echo.
echo 🌐 Your API will be available at: https://localhost

pause