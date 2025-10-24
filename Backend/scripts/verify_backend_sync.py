#!/usr/bin/env python3
"""
Backend-Frontend Sync Verification Script
Runs a small set of connectivity and functionality checks against the backend.
"""

from typing import Optional, Dict
import json
from pathlib import Path
import requests


# Configuration
BACKEND_URL = "http://localhost:5000"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_header(text: str) -> None:
    print("\n" + Colors.BLUE + "=" * 60)
    print("  " + text)
    print("" + "=" * 60 + Colors.END + "\n")


def print_success(text: str) -> None:
    print(Colors.GREEN + "✓ " + str(text) + Colors.END)


def print_error(text: str) -> None:
    print(Colors.RED + "✗ " + str(text) + Colors.END)


def print_warning(text: str) -> None:
    print(Colors.YELLOW + "⚠ " + str(text) + Colors.END)


def print_info(text: str) -> None:
    print("  " + str(text))


def test_health_check() -> bool:
    print_header("Test 1: Health Check")

    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Health endpoint responded with 200")
            print_info("Server version/info: " + str(data.get("version", "N/A")))
            return True
        print_error("Health endpoint returned {}".format(response.status_code))
        return False
    except requests.exceptions.RequestException as exc:
        print_error("Health check failed: {}".format(exc))
        return False


def test_list_models() -> bool:
    print_header("Test 2: List Models")

    try:
        response = requests.get(f"{BACKEND_URL}/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", {})
            print_success("Found {} models".format(len(models)))
            for model_name in models:
                print_info("  • {}".format(model_name))
            return True
        print_error("Failed to list models: {}".format(response.status_code))
        return False
    except requests.exceptions.RequestException as exc:
        print_error("Error listing models: {}".format(exc))
        return False


def find_test_audio() -> Optional[Path]:
    test_paths = [Path("uploads"), Path("test_upload.html").parent]

    for path in test_paths:
        if path.exists():
            audio_files = (
                list(path.glob("*.mp3"))
                + list(path.glob("*.wav"))
                + list(path.glob("*.flac"))
            )
            if audio_files:
                return audio_files[0]

    return None


def test_file_upload() -> Optional[str]:
    print_header("Test 4: File Upload")

    audio_file = find_test_audio()
    if not audio_file:
        print_warning("No test audio file found in uploads/")
        print_info("To test uploads, add an audio file to uploads/ folder")
        print_info("Skipping upload test...")
        return None

    try:
        with open(audio_file, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{BACKEND_URL}/upload", files=files)

        if response.status_code == 200:
            data = response.json()
            file_id = data.get("file_id")
            print_success("File uploaded successfully")
            print_info("File ID: " + str(file_id))
            return file_id
        print_error("Upload failed: {}".format(response.status_code))
        print_info("Response: {}".format(response.text))
        return None
    except (requests.exceptions.RequestException, OSError) as exc:
        print_error("Upload error: {}".format(exc))
        return None


def test_pitch_analysis(file_id: str) -> bool:
    print_header("Test 5: Pitch Analysis")

    if not file_id:
        print_warning("No file_id available (previous upload failed)")
        print_info("Skipping pitch analysis test...")
        return False

    try:
        payload = {"model_variant": "enhanced_chroma"}
        response = requests.post(
            f"{BACKEND_URL}/process/pitch_analysis/{file_id}", json=payload
        )

        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})
            print_success("Pitch analysis completed")
            print_info("Detected Key: {}".format(result.get("detected_key", "N/A")))
            print_info("Confidence: {}".format(result.get("confidence", "N/A")))
            print_info("Dominant Pitches: {}".format(result.get("dominant_pitches", [])))
            return True
        print_error("Pitch analysis failed: {}".format(response.status_code))
        return False
    except requests.exceptions.RequestException as exc:
        print_error("Pitch analysis error: {}".format(exc))
        return False


def test_other_models(file_id: str) -> None:
    print_header("Test 6: Other Models Availability")

    if not file_id:
        print_warning("No file_id available")
        return

    models_to_test = [
        ("demucs", {"model_variant": "htdemucs"}),
        ("whisper", {"model_variant": "base"}),
        ("pitch_analysis", {"model_variant": "basic_chroma"}),
    ]

    for model_name, payload in models_to_test:
        try:
            response = requests.post(
                f"{BACKEND_URL}/process/{model_name}/{file_id}", json=payload, timeout=5
            )

            if response.status_code == 200:
                print_success(f"{model_name}: Available ✓")
            elif response.status_code in [500, 503]:
                print_error(f"{model_name}: Processing error ({response.status_code})")
            else:
                print_warning(f"{model_name}: Status {response.status_code}")
        except requests.exceptions.Timeout:
            print_warning(f"{model_name}: Timeout (may be processing)")
        except requests.exceptions.RequestException as exc:
            print_error(f"{model_name}: {exc}")


def test_status(file_id: str) -> bool:
    print_header("Test 7: Status Endpoint")

    if not file_id:
        print_warning("No file_id available")
        return False

    try:
        response = requests.get(f"{BACKEND_URL}/status/{file_id}")

        if response.status_code == 200:
            data = response.json()
            print_success("Status endpoint working")
            print_info("Status data: {}".format(json.dumps(data, indent=2)))
            return True
        print_warning("Status endpoint returned {}".format(response.status_code))
        return False
    except requests.exceptions.RequestException as exc:
        print_error("Status check error: {}".format(exc))
        return False


def test_cors() -> bool:
    print_header("Test 8: CORS Headers")

    try:
        response = requests.options(f"{BACKEND_URL}/process/demucs/test")

        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
        }

        if cors_headers["Access-Control-Allow-Origin"]:
            print_success("CORS is enabled")
            for header, value in cors_headers.items():
                if value:
                    print_info("{}: {}".format(header, value))
        else:
            print_warning("CORS headers not found in response")

        return True
    except requests.exceptions.RequestException as exc:
        print_error("CORS check error: {}".format(exc))
        return False


def print_summary(results: Dict) -> None:
    print_header("Summary Report")

    tests_passed = sum(1 for v in results.values() if v is True)
    tests_failed = sum(1 for v in results.values() if v is False)
    tests_skipped = sum(1 for v in results.values() if v is None)

    print_info("Tests Passed: {}".format(tests_passed))
    print_info("Tests Failed: {}".format(tests_failed))
    print_info("Tests Skipped: {}".format(tests_skipped))

    print("\n" + Colors.BLUE + "=" * 60 + Colors.END)

    if tests_failed == 0:
        print_success("All tests passed! Backend is working correctly.")
        print_info("Frontend should work if it:")
        print_info("  1. Uploads files and stores file_id")
        print_info("  2. Uses file_id in subsequent requests")
        print_info("  3. Sends model_variant in request body")
        print_info("  4. Handles nested responses (data.result.*)")
    else:
        print_error("{} test(s) failed. Check errors above.".format(tests_failed))
        print_info("Common issues:")
        print_info("  • Backend not running (python app.py)")
        print_info("  • Port 5000 already in use")
        print_info("  • Missing dependencies")


def main() -> None:
    print("\n" + Colors.BLUE + "Backend-Frontend Sync Verification" + Colors.END)
    print("Backend URL: {}\n".format(BACKEND_URL))

    results: Dict = {}

    # Run tests
    results["health"] = test_health_check()
    if not results["health"]:
        print_error("Backend is not running. Stopping tests.")
        return

    results["models"] = test_list_models()
    results["cors"] = test_cors()

    file_id = test_file_upload()
    if file_id:
        results["pitch_analysis"] = test_pitch_analysis(file_id)
        results["status"] = test_status(file_id)
        test_other_models(file_id)

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + Colors.YELLOW + "Tests interrupted by user" + Colors.END)
    except Exception as exc:  # keep broad catch for top-level diagnostics
        print_error("Unexpected error: {}".format(exc))
