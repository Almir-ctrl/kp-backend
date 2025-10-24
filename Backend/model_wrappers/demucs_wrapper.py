import sys
import types

try:
    import torchaudio  # optional; used when available  # noqa: F401
except (ImportError, OSError):
    # Provide a dummy module to avoid import-time crashes on machines
    # without torchaudio binaries available.
    sys.modules['torchaudio'] = types.ModuleType('torchaudio')
