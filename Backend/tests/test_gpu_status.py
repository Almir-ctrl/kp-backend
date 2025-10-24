import requests
import os


# Simple smoke test for /gpu-status endpoint

def test_gpu_status_endpoint():
    base = os.environ.get('API_BASE_URL', 'http://127.0.0.1:5000')
    url = f"{base}/gpu-status"
    resp = requests.get(url, timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert 'available' in data
    assert 'torch_installed' in data
    # If torch is installed, expect boolean keys present
    if data.get('torch_installed'):
        assert isinstance(data.get('cuda_available'), bool)
        assert isinstance(data.get('gpu_count'), int)

    # Test passes if endpoint responds and contains the expected keys
