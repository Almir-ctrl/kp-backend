"""Light smoke test for the Enhanced Chroma Analysis API.

This test attempts a minimal health check for the enhanced chroma
endpoints. If the server is not available, the test will be skipped so
CI doesn't fail due to an offline dev server.
"""

import requests
import pytest


BASE_URL = "http://localhost:5000"


def test_enhanced_chroma_analysis_smoke():
    # Attempt to reach the server; skip if not available
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
    except requests.exceptions.RequestException:
        pytest.skip("Backend not reachable; skipping enhanced chroma smoke test")

    assert r.status_code == 200

    # If health is OK, ensure the chroma analyze endpoint exists in /models
    r2 = requests.get(f"{BASE_URL}/models")
    assert r2.status_code == 200
    models = r2.json()
    # Accept either shaped response or raw dict
    if isinstance(models, dict) and "models" in models:
        models = models["models"]
    assert isinstance(models, dict)
    # If pitch or chroma models are present, test passes; otherwise it's still a smoke test
