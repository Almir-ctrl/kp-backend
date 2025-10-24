#!/usr/bin/env python3
"""
Test script for MusicGen text-to-music generation
"""

import requests


def test_musicgen():
    """Test MusicGen API endpoint"""

    base_url = "http://localhost:5000"

    # Test health endpoint first
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # Test models endpoint
    print("\nTesting models endpoint...")
    try:
        response = requests.get(f"{base_url}/models")
        print(f"Models: {response.status_code}")
        models_data = response.json()
        print(f"Available models: {list(models_data['models'].keys())}")
    except Exception as e:
        print(f"Models check failed: {e}")

    # Test MusicGen generation
    print("\nTesting MusicGen generation...")

    generation_data = {
        "prompt": "upbeat electronic dance music with synthesizers and drums",
        "model_variant": "small",
        "duration": 10,
        "temperature": 1.0,
        "cfg_coeff": 3.0,
    }

    try:
        response = requests.post(
            f"{base_url}/generate/text-to-music",
            json=generation_data,
            headers={"Content-Type": "application/json"},
        )

        print(f"Generation response: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Generation successful!")
            print(f"File ID: {result['file_id']}")
            print(f"Download URL: {result['download_url']}")
            print(f"Generation details: {result['result']}")

            # Test status endpoint
            file_id = result["file_id"]
            print(f"\nTesting status for file_id: {file_id}")

            status_response = requests.get(
                f"{base_url}/generate/text-to-music/{file_id}"
            )
            print(f"Status response: {status_response.status_code}")

            if status_response.status_code == 200:
                status_data = status_response.json()
                print("✅ Status check successful!")
                print(f"Status: {status_data['status']}")
                print(
                    f"Generated files: {len(status_data['generated_files'])}"
                )
                for file_info in status_data["generated_files"]:
                    print(
                        f"  - {file_info['filename']} ({file_info['size_mb']} MB)"
                    )
            else:
                print(f"❌ Status check failed: {status_response.text}")
        else:
            print(f"❌ Generation failed: {response.text}")

    except Exception as e:
        print(f"❌ Generation test failed: {e}")


if __name__ == "__main__":
    print("🎵 MusicGen API Test Script")
    print("=" * 40)
    test_musicgen()
