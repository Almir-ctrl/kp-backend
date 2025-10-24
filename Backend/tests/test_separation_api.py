#!/usr/bin/env python3
"""
Test script for audio separation API
"""
import os
import requests
import pytest


def test_separation():
    """Integration-style separation test. Skips when test audio missing."""

    test_audio = os.path.join("uploads", "test_audio.wav")
    if not os.path.exists(test_audio):
        pytest.skip("Test audio not available: uploads/test_audio.wav")

    url = "http://localhost:5000/process/demucs"
    with open(test_audio, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)

    assert response.status_code == 200, (
        f"Demucs processing failed: {response.status_code} - {response.text}"
    )

    result = response.json()
    assert isinstance(result, dict)
    assert "tracks" in result
    assert result["tracks"], "Expected at least one separated track"


# Test module is pytest-compatible; manual execution helper removed.
