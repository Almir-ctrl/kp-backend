#!/usr/bin/env python
"""Test the /models/gemma_3n endpoint."""
import sys
import time
import requests
import json

# Wait for server to be ready
time.sleep(3)

try:
    # Test the endpoint
    url = "http://127.0.0.1:5000/models/gemma_3n"
    print(f"Testing: {url}", file=sys.stderr)

    response = requests.get(url, timeout=5)

    print(f"Status Code: {response.status_code}", file=sys.stderr)
    print(f"Response Length: {len(response.text)}", file=sys.stderr)

    if response.status_code == 200:
        data = response.json()
        print("SUCCESS! JSON Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"ERROR: Status {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(1)
