#!/usr/bin/env python3
"""
Test transcription API endpoints
"""
import os
import requests
import pytest


def test_transcription_endpoint():
    """Integration-style test for the transcription endpoint.

    Skips when the local test audio file is not present. Uses assertions
    so pytest treats failures properly.
    """

    url = "http://localhost:5000/transcribe"
    test_audio = os.path.join("uploads", "test_audio.wav")

    if not os.path.exists(test_audio):
        pytest.skip("Test audio not available: uploads/test_audio.wav")

    # Use a small model for CI/dev speed
    with open(test_audio, "rb") as f:
        files = {"file": f}
        data = {"model": "tiny"}
        response = requests.post(url, files=files, data=data)

    assert response.status_code == 200, (
        f"Transcription request failed: {response.status_code} - {response.text}"
    )

    result = response.json()
    assert isinstance(result, dict), "Expected JSON object in response"
    assert "transcription" in result, "Missing 'transcription' in response"


def test_health_endpoints():
    endpoints = [
        "http://localhost:5000/status",
        "http://localhost:5000/health",
        "http://localhost:5000/models",
    ]

    for endpoint in endpoints:
        response = requests.get(endpoint)
        assert (
            response.status_code == 200
        ), f"Health endpoint {endpoint} returned {response.status_code}"


# Tests are intended to be run with pytest. Manual execution helper removed.
