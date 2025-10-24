#!/usr/bin/env python3
"""Test Whisper transcription directly (pytest-style)."""
import whisper
import os
import pytest


def test_whisper_direct():
    file_path = "uploads/641443c6-cf0e-4881-b656-2a9f53cfee7a.mp3"
    if not os.path.exists(file_path):
        pytest.skip("Whisper test file not present; skipping")

    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    assert isinstance(result, dict)
    assert "text" in result and result["text"].strip()
