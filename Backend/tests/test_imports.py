"""Test if Demucs and Gemma imports work in the virtual environment."""
import sys

print("=" * 60)
print("TESTING IMPORTS IN VIRTUAL ENVIRONMENT")
print("=" * 60)
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print()

# Test Demucs
print("1. Testing Demucs...")
try:
    import importlib
    importlib.import_module('demucs')
    print("   ✅ demucs imported successfully")
except ImportError as e:
    print(f"   ❌ demucs import failed: {e}")

# Test Gemma dependencies
print("\n2. Testing Gemma 3n dependencies...")
try:
    import importlib
    importlib.import_module('transformers')
    print("   ✅ transformers imported successfully")
except ImportError as e:
    print(f"   ❌ transformers import failed: {e}")

try:
    import torch
    print(f"   ✅ torch imported successfully (version: {torch.__version__})")
except ImportError as e:
    print(f"   ❌ torch import failed: {e}")

try:
    import librosa
    print(f"   ✅ librosa imported successfully (version: {librosa.__version__})")
except ImportError as e:
    print(f"   ❌ librosa import failed: {e}")

try:
    import soundfile
    print(f"   ✅ soundfile imported successfully (version: {soundfile.__version__})")
except ImportError as e:
    print(f"   ❌ soundfile import failed: {e}")

try:
    import accelerate
    print(f"   ✅ accelerate imported successfully (version: {accelerate.__version__})")
except ImportError as e:
    print(f"   ❌ accelerate import failed: {e}")

try:
    import sentencepiece
    print(f"   ✅ sentencepiece imported successfully (version: {sentencepiece.__version__})")
except ImportError as e:
    print(f"   ❌ sentencepiece import failed: {e}")

# Test Flask-SocketIO
print("\n3. Testing Flask-SocketIO...")
try:
    import importlib
    importlib.import_module('flask_socketio')
    print("   ✅ flask_socketio imported successfully")
except ImportError as e:
    print(f"   ❌ flask_socketio import failed: {e}")

# Test models.py
print("\n4. Testing models.py processors...")
try:
    from models import get_processor
    print("   ✅ models.get_processor imported successfully")

    # Try to get Demucs processor
    try:
        demucs_proc = get_processor('demucs')
        print(f"   ✅ Demucs processor created: {type(demucs_proc).__name__}")
    except Exception as e:
        print(f"   ❌ Demucs processor failed: {e}")

    # Try to get Gemma processor
    try:
        gemma_proc = get_processor('gemma_3n')
        print(f"   ✅ Gemma 3n processor created: {type(gemma_proc).__name__}")
    except Exception as e:
        print(f"   ❌ Gemma 3n processor failed: {e}")

except ImportError as e:
    print(f"   ❌ models import failed: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
