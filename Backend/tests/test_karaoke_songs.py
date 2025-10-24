#!/usr/bin/env python3
"""Test /karaoke/songs endpoint returns proper Song metadata."""

import requests
import pytest

BASE_URL = "http://127.0.0.1:5000"


def test_karaoke_songs_endpoint():
    try:
        response = requests.get(f"{BASE_URL}/karaoke/songs", timeout=5)
    except requests.exceptions.ConnectionError:
        pytest.skip("Backend not running on http://127.0.0.1:5000")

    assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
    data = response.json()
    songs = data.get("songs", [])
    count = data.get("count", 0)

    if count == 0:
        pytest.skip("No karaoke songs found; create outputs/Karaoke-pjesme and re-run tests")

    song = songs[0]
    required_fields = ["id", "title", "artist", "url", "file_id"]
    missing_fields = [field for field in required_fields if field not in song]
    assert not missing_fields, f"Missing fields: {missing_fields}"

    # Basic sanity checks
    assert song["url"] and "undefined" not in song["url"], "Invalid URL in song metadata"
    assert song["title"], "Missing title"
