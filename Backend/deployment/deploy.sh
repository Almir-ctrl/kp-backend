#!/bin/bash
# Production deployment script for Linux/Mac

echo "🚀 Deploying Demucs Backend for Production..."

# Create production environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your production values!"
fi

# Install production dependencies
echo "📦 Installing production dependencies..."
pip install -r requirements-prod.txt

# Create necessary directories
mkdir -p uploads outputs

# Set proper permissions (adjust as needed)
chmod 755 uploads outputs

echo "✅ Deployment preparation complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Edit .env file with your production values"
echo "2. Run with: gunicorn --config gunicorn.conf.py wsgi:app"
echo "3. Or use Docker: docker-compose up -d"