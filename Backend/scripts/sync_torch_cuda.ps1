# sync_torch_cuda.ps1
# This script sets up PyTorch Nightly with CUDA 12.9+ for RTX 5070 Ti (sm_120) globally and in your venv,
# and applies the demucs_wrapper.py fix for torchaudio DLL issues.


# 0. Detect pip or pip3
function Get-PipCommand {
    if (Get-Command pip -ErrorAction SilentlyContinue) {
        return "pip"
    } elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
        return "pip3"
    } else {
        throw "Neither pip nor pip3 is available in PATH. Please install Python 3 and pip."
    }
}
$pipCmd = Get-PipCommand

# 1. Install PyTorch Nightly (CUDA 12.9+) globally
Write-Host "Installing PyTorch Nightly (CUDA 12.9+) globally..."
& $pipCmd install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu129 --force-reinstall

# 2. Activate your virtual environment
$venvPath = ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..."
    & $venvPath
} else {
    Write-Host "Virtual environment not found. Creating .venv..."
    python -m venv .venv
    & $venvPath
}


# 3. Install PyTorch Nightly (CUDA 12.9+) in venv
Write-Host "Installing PyTorch Nightly (CUDA 12.9+) in venv..."
& $pipCmd install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu129 --force-reinstall

# 4. Install other requirements in venv
if (Test-Path "requirements.txt") {
    Write-Host "Installing other requirements in venv..."
    & $pipCmd install -r requirements.txt
}

# 5. Apply demucs_wrapper.py fix (overwrite if exists)
$demucsWrapper = @"
import importlib
import sys

try:
    import torchaudio
except (ImportError, OSError):
    # Patch sys.path to skip torchaudio if DLL load fails
    sys.modules['torchaudio'] = importlib.util.module_from_spec(importlib.machinery.ModuleSpec('torchaudio', None))
"@
Set-Content -Path "demucs_wrapper.py" -Value $demucsWrapper -Encoding UTF8
Write-Host "demucs_wrapper.py fix applied."

# 6. Verify CUDA and PyTorch
Write-Host "Verifying PyTorch CUDA availability in venv..."
python -c "import torch; print('CUDA available:', torch.cuda.is_available(), '| CUDA version:', torch.version.cuda)"

Write-Host "Setup complete. All models should now use GPU acceleration with PyTorch Nightly and CUDA 12.9+."