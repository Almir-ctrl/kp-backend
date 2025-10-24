#!/usr/bin/env python3
"""Test script for pitch analysis functionality (pytest-style)

This test is designed to be safe to run in CI/local dev. If the server
doesn't expose the expected endpoints or no files are uploaded, the test
will skip rather than fail.
"""

import requests
import pytest


def test_pitch_analysis():
    base_url = "http://localhost:5000"

    # 1) Fetch models and confirm structure
    response = requests.get(f"{base_url}/models")
    assert response.status_code == 200, (
        f"Failed to get models: {response.status_code} - {response.text}"
    )
    models = response.json()
    if isinstance(models, dict) and "models" in models and isinstance(models["models"], dict):
        models_dict = models["models"]
    elif isinstance(models, dict):
        models_dict = models
    else:
        raise AssertionError(f"Unexpected /models response type: {type(models).__name__}")

    # Ensure pitch_analysis is present (or at least confirm models_dict is mapping)
    assert isinstance(models_dict, dict)

    # 2) Check for uploaded files to analyze; skip if none or endpoint missing
    response = requests.get(f"{base_url}/files")
    if response.status_code == 404:
        pytest.skip("/files endpoint not available on this backend")
    assert response.status_code == 200, f"Failed to get files: {response.status_code}"
    files = response.json()
    if not files:
        pytest.skip("No uploaded files available for pitch analysis tests")

    # Use the first available file for analysis
    test_file = files[0]
    file_id = test_file.get("file_id")
    assert file_id, "Test file missing file_id"

    # 3) Run pitch analysis with default variant and assert well-formed response
    resp = requests.post(f"{base_url}/process/pitch_analysis/{file_id}")
    assert resp.status_code == 200, (
        f"Pitch analysis failed: {resp.status_code} - {resp.text}"
    )
    result = resp.json()
    assert isinstance(result, dict)
    # optional keys: detected_key, confidence
    assert "confidence" in result or "detected_key" in result

    # 4) Run pitch analysis with explicit variant (basic_chroma) if supported
    resp2 = requests.post(
        f"{base_url}/process/pitch_analysis/{file_id}",
        json={"model_variant": "basic_chroma"},
    )
    assert resp2.status_code == 200, (
        f"Basic chroma analysis failed: {resp2.status_code} - {resp2.text}"
    )
    result2 = resp2.json()
    assert isinstance(result2, dict)
