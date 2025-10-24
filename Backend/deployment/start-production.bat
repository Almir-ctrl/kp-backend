@echo off
echo 🚀 Starting Demucs Backend in Production Mode...

REM Check if virtual environment exists
if not exist .venv (
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install production dependencies
echo 📥 Installing dependencies...
pip install -r requirements-prod.txt

REM Create .env if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    copy .env.example .env
    echo ⚠️  Edit .env file with your production settings!
    pause
)

REM Create directories
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs

REM Start the server in production mode
echo 🌟 Starting production server...
echo Server will be available at: http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

python production.py