import requests
import os
import time

BASE_URL = "http://localhost:5000"


def find_test_file():
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    if not os.path.exists(uploads_dir):
        return None
    for f in os.listdir(uploads_dir):
        if f.lower().endswith((".mp3", ".wav")):
            return os.path.join(uploads_dir, f)
    return None


def test_duplicate_upload_flow():
    """Upload the same file twice. Second upload should return 409 or 200."""
    test_file = find_test_file()
    assert test_file is not None, "No test audio file found in uploads/"

    with open(test_file, "rb") as f:
        files = {"file": (os.path.basename(test_file), f, "audio/mpeg")}
        r1 = requests.post(
            f"{BASE_URL}/upload", files=files, data={"auto_process": "false"}
        )

    assert r1.status_code in (200, 409), "Unexpected status for first upload"
    data1 = r1.json()
    if r1.status_code == 200:
        assert "file_id" in data1

    time.sleep(0.5)

    with open(test_file, "rb") as f2:
        files2 = {"file": (os.path.basename(test_file), f2, "audio/mpeg")}
        r2 = requests.post(
            f"{BASE_URL}/upload", files=files2, data={"auto_process": "false"}
        )

    assert r2.status_code in (200, 409), "Unexpected status for duplicate upload"

    if r2.status_code == 409:
        data2 = r2.json()
        assert data2.get("existing") is True
        assert "file_id" in data2
