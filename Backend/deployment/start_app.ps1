# Startup script for AiMusicSeparator Backend
# This ensures the correct virtual environment is used

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   AI MUSIC SEPARATOR BACKEND - STARTUP" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Define paths
$VENV_PATH = "C:\Users\almir\AiMusicSeparator-Backend\api\.venv"
$PYTHON_EXE = "$VENV_PATH\Scripts\python.exe"
$APP_SCRIPT = "app.py"

# Check if virtual environment exists
if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "❌ Virtual environment not found at: $VENV_PATH" -ForegroundColor Red
    Write-Host "   Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VENV_PATH
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & $PYTHON_EXE -m pip install --upgrade pip
    & $PYTHON_EXE -m pip install -r requirements.txt
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
}

# Verify dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$CHECK_DEPS = & $PYTHON_EXE -c "import transformers, torch, librosa, soundfile, accelerate, sentencepiece; print('OK')" 2>&1

if ($CHECK_DEPS -notmatch "OK") {
    Write-Host "❌ Missing dependencies detected" -ForegroundColor Red
    Write-Host "   Installing missing packages..." -ForegroundColor Yellow
    & $PYTHON_EXE -m pip install transformers torch librosa soundfile accelerate sentencepiece
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
}

Write-Host "✅ All dependencies verified" -ForegroundColor Green
Write-Host ""

# Display environment info
Write-Host "Environment Information:" -ForegroundColor Cyan
Write-Host "  Python: $PYTHON_EXE" -ForegroundColor Gray
$PYTHON_VERSION = & $PYTHON_EXE --version
Write-Host "  Version: $PYTHON_VERSION" -ForegroundColor Gray
Write-Host "  App: $APP_SCRIPT" -ForegroundColor Gray
Write-Host ""


# Print CUDA and PyTorch version info
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   PYTORCH & CUDA ENVIRONMENT CHECK" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
$cuda_version = & $PYTHON_EXE -c "import torch; print(getattr(torch.version, 'cuda', 'N/A'))"
$torch_version = & $PYTHON_EXE -c "import torch; print(torch.__version__)"
$gpu_name = & $PYTHON_EXE -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU detected')"
Write-Host "PyTorch version: $torch_version" -ForegroundColor Gray
Write-Host "CUDA version: $cuda_version" -ForegroundColor Gray
Write-Host "GPU: $gpu_name" -ForegroundColor Gray
Write-Host ""
if ($gpu_name -eq "No CUDA GPU detected") {
    Write-Host "⚠️  No CUDA GPU detected. The backend will run on CPU only." -ForegroundColor Yellow
} else {
    Write-Host "✅ CUDA GPU detected: $gpu_name" -ForegroundColor Green
}
Write-Host ""
Write-Host "Setting CUDA_LAUNCH_BLOCKING=1 for debugging..." -ForegroundColor Yellow
$env:CUDA_LAUNCH_BLOCKING = "1"
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   STARTING SERVER..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server will be available at:" -ForegroundColor Green
Write-Host "  • http://localhost:5000" -ForegroundColor White
Write-Host "  • http://192.168.0.13:5000" -ForegroundColor White
Write-Host ""
Write-Host "Test UI available at:" -ForegroundColor Green
Write-Host "  • http://localhost:5000/test_progress.html" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run the app with the virtual environment Python and CUDA_LAUNCH_BLOCKING=1
& $PYTHON_EXE $APP_SCRIPT
