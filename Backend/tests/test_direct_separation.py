"""Direct test of Demucs separation functionality"""
import os
import subprocess
import pytest


def test_direct_separation():
    """Run Demucs separation on a test file and check for vocals output."""

    input_file = "uploads/test_audio.wav"
    output_dir = "outputs"
    model = "htdemucs"

    if not os.path.exists(input_file):
        pytest.skip(f"Input file {input_file} not found")

    # Ensure demucs is available (module or CLI)
    # Check if demucs is available without importing to avoid unused-import lint
    import importlib.util

    if importlib.util.find_spec("demucs") is None:
        pytest.skip("Demucs not installed in this environment; skipping direct separation")

    cmd = [
        os.sys.executable,
        "-m",
        "demucs",
        "-n",
        model,
        "--mp3",
        "-o",
        output_dir,
        input_file,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    assert result.returncode == 0, f"Demucs subprocess failed: {result.stderr}"

    filename_without_ext = os.path.splitext(os.path.basename(input_file))[0]
    expected_output_dir = os.path.join(output_dir, model, filename_without_ext)
    assert (
        os.path.exists(expected_output_dir)
    ), f"Expected output directory missing: {expected_output_dir}"

    tracks = [
        os.path.splitext(tf)[0]
        for tf in os.listdir(expected_output_dir)
        if tf.endswith(".mp3")
    ]
    assert "vocals" in tracks, "No vocals track found in Demucs output"
