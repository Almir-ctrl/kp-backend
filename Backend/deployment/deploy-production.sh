#!/bin/bash
# Production Deployment Script
# Deploys AI backend with production-grade Gunicorn server

set -e

echo "🏭 Starting Production Deployment..."
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose."
    exit 1
fi

echo "✅ Docker and docker-compose are available"

# Generate SSL certificates if they don't exist
if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
    echo "🔐 Generating SSL certificates..."
    mkdir -p nginx/ssl
    
    # Generate self-signed certificate for development
    docker run --rm -v "${PWD}/nginx/ssl:/certs" alpine/openssl req -x509 \
        -newkey rsa:2048 \
        -keyout /certs/key.pem \
        -out /certs/cert.pem \
        -days 365 \
        -nodes \
        -subj "/C=US/ST=State/L=City/O=AI-Backend/CN=localhost"
    
    echo "✅ SSL certificates generated"
else
    echo "✅ SSL certificates already exist"
fi

# Set production environment variables
echo "⚙️  Setting up production environment..."
cat > .env << EOF
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
PORT=8000
CORS_ORIGINS=*
WORKERS=4
WORKER_CLASS=eventlet
GUNICORN_CMD_ARGS="--config gunicorn_production.conf.py"
EOF

echo "✅ Environment configured"

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans

# Build and start production containers
echo "🚀 Building and starting production containers..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service health..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running"
    
    # Test health endpoint
    echo "🏥 Testing health endpoint..."
    if curl -k -s https://localhost/health > /dev/null; then
        echo "✅ Health check passed"
        
        echo ""
        echo "🎉 Production deployment successful!"
        echo "=================================="
        echo "🌐 HTTPS Server: https://localhost"
        echo "🔌 WebSocket: wss://localhost/transcribe"
        echo "🏥 Health Check: https://localhost/health"
        echo "📊 API Docs: https://localhost/models"
        echo ""
        echo "📋 Management Commands:"
        echo "  View logs: docker-compose logs -f"
        echo "  Stop services: docker-compose down"
        echo "  Restart: docker-compose restart"
        echo ""
        echo "⚠️  Note: Accept SSL certificate warning in browser"
        echo "   (Click Advanced → Proceed to localhost)"
        
    else
        echo "❌ Health check failed"
        echo "📋 Check logs: docker-compose logs ai-backend"
        exit 1
    fi
else
    echo "❌ Services failed to start"
    echo "📋 Check status: docker-compose ps"
    echo "📋 Check logs: docker-compose logs"
    exit 1
fi