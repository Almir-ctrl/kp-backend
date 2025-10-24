#!/usr/bin/env python
"""Run backend in subprocess and test endpoints."""
import subprocess
import time
import requests
import json

# Start Flask backend in subprocess
print("Starting Flask backend...")
backend_process = subprocess.Popen(
    [".venv/Scripts/python", "app.py"],
    cwd=r"c:\Users\almir\AiMusicSeparator-Backend",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Give Flask time to start
print("Waiting for backend to start...")
time.sleep(5)

try:
    # Test basic health check
    print("\n" + "="*60)
    print("Testing /status endpoint...")
    r = requests.get("http://127.0.0.1:5000/status", timeout=5)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text}")

    # Test /models/gemma_3n
    print("\n" + "="*60)
    print("Testing /models/gemma_3n endpoint...")
    r = requests.get("http://127.0.0.1:5000/models/gemma_3n", timeout=5)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        print("Response (JSON):")
        print(json.dumps(r.json(), indent=2))
    else:
        print(f"Response: {r.text[:500]}")

    # Test /models endpoint
    print("\n" + "="*60)
    print("Testing /models endpoint...")
    r = requests.get("http://127.0.0.1:5000/models", timeout=5)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        print("Response has models:", list(r.json().get('models', {}).keys()))
    else:
        print(f"Response: {r.text[:500]}")

    print("\n" + "="*60)
    print("✅ All tests completed!")

except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")

finally:
    # Terminate backend
    print("\nStopping backend...")
    backend_process.terminate()
    backend_process.wait(timeout=5)
    print("Backend stopped.")
