"""
Compatibility shim: re-export everything from the file accidentally named
`configuration_wisper.py` (missing 'h'). Many internal imports expect
`configuration_whisper.py`, so this shim avoids editing all callers.
"""
from .configuration_wisper import (
    WhisperConfig,
    WhisperOnnxConfig,
)  # noqa: F401

__all__ = ["WhisperConfig", "WhisperOnnxConfig"]
