@echo off
REM Production Deployment Script for Windows
REM Deploys AI backend with production-grade Gunicorn server

echo 🏭 Starting Production Deployment...
echo ==================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker first.
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ docker-compose not found. Please install docker-compose.
    exit /b 1
)

echo ✅ Docker and docker-compose are available

REM Generate SSL certificates if they don't exist
if not exist "nginx\ssl\cert.pem" (
    echo 🔐 Generating SSL certificates...
    mkdir nginx\ssl 2>nul
    
    REM Generate self-signed certificate for development
    docker run --rm -v "%CD%/nginx/ssl:/certs" alpine/openssl req -x509 -newkey rsa:2048 -keyout /certs/key.pem -out /certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=AI-Backend/CN=localhost"
    
    echo ✅ SSL certificates generated
) else (
    echo ✅ SSL certificates already exist
)

REM Set production environment variables
echo ⚙️ Setting up production environment...
(
echo DEBUG=False
echo SECRET_KEY=production-secret-key-change-this-in-real-deployment
echo PORT=8000
echo CORS_ORIGINS=*
echo WORKERS=4
echo WORKER_CLASS=eventlet
echo GUNICORN_CMD_ARGS=--config gunicorn_production.conf.py
) > .env

echo ✅ Environment configured

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker-compose down --remove-orphans

REM Build and start production containers
echo 🚀 Building and starting production containers...
docker-compose up -d --build

REM Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 15 /nobreak >nul

REM Check if services are running
echo 🔍 Checking service health...
docker-compose ps | findstr "Up" >nul
if %errorlevel% equ 0 (
    echo ✅ Services are running
    
    REM Test health endpoint
    echo 🏥 Testing health endpoint...
    curl -k -s https://localhost/health >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Health check passed
        
        echo.
        echo 🎉 Production deployment successful!
        echo ==================================
        echo 🌐 HTTPS Server: https://localhost
        echo 🔌 WebSocket: wss://localhost/transcribe
        echo 🏥 Health Check: https://localhost/health
        echo 📊 API Docs: https://localhost/models
        echo.
        echo 📋 Management Commands:
        echo   View logs: docker-compose logs -f
        echo   Stop services: docker-compose down
        echo   Restart: docker-compose restart
        echo.
        echo ⚠️ Note: Accept SSL certificate warning in browser
        echo    ^(Click Advanced → Proceed to localhost^)
        
    ) else (
        echo ❌ Health check failed
        echo 📋 Check logs: docker-compose logs ai-backend
        exit /b 1
    )
) else (
    echo ❌ Services failed to start
    echo 📋 Check status: docker-compose ps
    echo 📋 Check logs: docker-compose logs
    exit /b 1
)

pause