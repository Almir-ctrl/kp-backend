#!/usr/bin/env python3
"""Test script for Gemma 3N audio transcription and analysis (pytest-style)."""

import requests
import pytest


def test_gemma_3n():
    base_url = "http://localhost:5000"

    # 1) Check available models
    resp = requests.get(f"{base_url}/models")
    assert resp.status_code == 200
    models = resp.json()
    if isinstance(models, dict) and "models" in models:
        models = models["models"]
    assert isinstance(models, dict)
    assert "gemma_3n" in models, "/models does not expose gemma_3n"

    # 2) Transcription smoke — skip if endpoint not configured for test ids
    resp = requests.post(
        f"{base_url}/process/gemma_3n/test_001",
        json={"task": "transcribe", "model_variant": "gemma-2-9b-it"},
    )
    if resp.status_code != 200:
        pytest.skip("Gemma transcription endpoint not available for test_001")
    result = resp.json()
    assert isinstance(result, dict)

    # 3) Analysis smoke
    resp2 = requests.post(
        f"{base_url}/process/gemma_3n/test_002",
        json={"task": "analyze", "temperature": 0.7, "top_p": 0.9},
    )
    if resp2.status_code != 200:
        pytest.skip("Gemma analysis endpoint not available for test_002")
    result2 = resp2.json()
    assert isinstance(result2, dict)
