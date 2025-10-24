#!/usr/bin/env python3
"""
Complete API testing script
"""
import requests


def test_all_endpoints():
    base_url = "http://localhost:5000"

    # Health endpoint
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

    # Status endpoint
    response = requests.get(f"{base_url}/status")
    assert response.status_code == 200
    status_data = response.json()
    assert "status" in status_data

    # Models endpoint
    response = requests.get(f"{base_url}/models")
    assert response.status_code == 200
    models_data = response.json()
    assert isinstance(models_data, dict)


if __name__ == "__main__":
    test_all_endpoints()
