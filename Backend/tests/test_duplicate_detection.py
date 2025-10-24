"""Test duplicate upload detection and skip logic."""
import os
import requests
import pytest

BASE_URL = "http://localhost:5000"


def test_duplicate_upload():
    """Test uploading the same file twice."""
    uploads_dir = "uploads"
    test_file = None
    if os.path.exists(uploads_dir):
        files = [f for f in os.listdir(uploads_dir) if f.endswith((".mp3", ".wav"))]
        if files:
            test_file = os.path.join(uploads_dir, files[0])

    if not test_file:
        pytest.skip("No test files found in uploads/")

    # First upload
    with open(test_file, "rb") as f:
        files_payload = {"file": (os.path.basename(test_file), f, "audio/mpeg")}
        response1 = requests.post(
            f"{BASE_URL}/upload", files=files_payload, data={"auto_process": "false"}
        )

    # First upload: can be 200 (fresh upload) or 409 (already present)
    if response1.status_code == 200:
        file_id1 = response1.json().get("file_id")
        assert file_id1, "First upload did not return file_id"

        # Second upload (should be detected as duplicate)
        with open(test_file, "rb") as f:
            files_payload = {"file": (os.path.basename(test_file), f, "audio/mpeg")}
            response2 = requests.post(
                f"{BASE_URL}/upload",
                files=files_payload,
                data={"auto_process": "false"},
            )

        assert (
            response2.status_code == 409
        ), f"Expected 409 on duplicate upload, got {response2.status_code}"
        data2 = response2.json()
        assert (
            data2.get("existing") is True or data2.get("file_id")
        ), "Duplicate response missing existing/file_id"
    elif response1.status_code == 409:
        # Already uploaded in prior run; ensure response includes file_id or existing flag
        data1 = response1.json()
        assert (
            data1.get("existing") is True or data1.get("file_id")
        ), "Duplicate response missing existing/file_id"
    else:
        pytest.fail(f"Unexpected status on first upload: {response1.status_code}")


def test_skip_existing_output():
    """Test skipping re-processing when output already exists."""

    # Find a file_id with existing vocals
    outputs_dir = "outputs"
    existing_file_id = None

    if os.path.exists(outputs_dir):
        for dir_name in os.listdir(outputs_dir):
            dir_path = os.path.join(outputs_dir, dir_name)
            if os.path.isdir(dir_path):
                vocals_path = os.path.join(dir_path, "vocals.mp3")
                if os.path.exists(vocals_path):
                    existing_file_id = dir_name
                    break

    if not existing_file_id:
        pytest.skip("No existing vocals found in outputs/")

    # Try to process Demucs again (should skip)
    response = requests.post(f"{BASE_URL}/process/demucs/{existing_file_id}")
    assert response.status_code == 200, f"Process endpoint returned {response.status_code}"
    data = response.json()
    assert data.get("skipped"), f"Expected skipped=True, got: {data}"
    assert data.get("existing_output")


# Manual run harness removed; run tests with pytest.
