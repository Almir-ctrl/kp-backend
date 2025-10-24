#!/bin/bash
echo "🚀 Starting Demucs Backend in Production Mode..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install production dependencies
echo "📥 Installing dependencies..."
pip install -r requirements-prod.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Edit .env file with your production settings!"
    read -p "Press enter to continue..."
fi

# Create directories
mkdir -p uploads outputs

# Start the server with Gunicorn
echo "🌟 Starting production server..."
echo "Server will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""

gunicorn --config gunicorn.conf.py wsgi:app