@echo off
REM Production deployment script for Windows

echo 🚀 Deploying Demucs Backend for Production...

REM Create production environment file
if not exist .env (
    echo 📝 Creating .env file...
    copy .env.example .env
    echo ⚠️  Please edit .env file with your production values!
)

REM Activate virtual environment and install dependencies
echo 📦 Installing production dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements-prod.txt

REM Create necessary directories
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs

echo ✅ Deployment preparation complete!
echo.
echo 🔧 Next steps:
echo 1. Edit .env file with your production values
echo 2. Run with: gunicorn --config gunicorn.conf.py wsgi:app
echo 3. Or use Docker: docker-compose up -d

pause