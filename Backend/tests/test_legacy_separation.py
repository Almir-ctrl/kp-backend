#!/usr/bin/env python3
"""
Test legacy separation endpoint
"""
import requests
import uuid


def test_legacy_separation():
    print("Testing legacy separation API...")

    # Generate a file ID
    file_id = str(uuid.uuid4())

    # Test the legacy separate endpoint
    url = f"http://localhost:5000/separate/{file_id}"

    try:
        # First upload a file (copy test file with new name)
        import shutil
        shutil.copy("uploads/test_audio.wav", f"uploads/{file_id}.wav")
        print("Uploaded file as", f"{file_id}.wav")

        # Then call separate endpoint
        response = requests.post(url)

        print("Response status:", response.status_code)
        print("Response content:", response.text)

        if response.status_code == 200:
            result = response.json()
            print("Separation successful!")
            print("Tracks:", result.get('tracks', []))
            return result

        print("Separation failed!")
        return None

    except Exception as exc:
        print("Error:", exc)
        return None


if __name__ == "__main__":
    test_legacy_separation()
