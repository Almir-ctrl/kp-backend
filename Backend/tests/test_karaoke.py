"""Test karaoke generation functionality."""
from pathlib import Path
import pytest
from models import get_processor
from flask import current_app


def test_karaoke_generation():
    """Integration-style karaoke test.

    Skips when no uploads are present. Uses assertions rather than returning
    booleans so pytest reports failures consistently.
    """

    upload_folder = Path("uploads")
    test_files = list(upload_folder.glob("*.mp3"))
    if not test_files:
        pytest.skip("No test files found in uploads folder")

    test_file = test_files[0]
    file_id = test_file.stem

    output_base = Path("outputs")
    demucs_output = None

    htdemucs_dir = output_base / "htdemucs" / file_id
    if htdemucs_dir.exists():
        demucs_output = htdemucs_dir
    else:
        direct_output = output_base / file_id / "htdemucs"
        if direct_output.exists():
            demucs_output = direct_output

    if not demucs_output:
        # Running processors requires a Flask application context. Skip
        # when tests are executed outside the running server environment.
        try:
            _ = current_app.name  # type: ignore
        except RuntimeError:
            pytest.skip("Requires running Flask app context to execute processors")

        # Best-effort attempt to run separation if outputs missing
        demucs_processor = get_processor("demucs")
        result = demucs_processor.process(
            file_id,
            test_file,
            model_variant="htdemucs",
        )
        demucs_output = Path(result.get("output_dir", ""))

    instrumental_file = None
    vocals_file = None
    for f in demucs_output.iterdir():
        if f.is_file():
            if "no_vocals" in f.name or "instrumental" in f.name:
                instrumental_file = str(f)
            elif "vocals" in f.name:
                vocals_file = str(f)

    assert instrumental_file, "No instrumental track found in Demucs output"

    transcription_file = output_base / file_id / f"{file_id}_transcription.txt"
    transcription_text = ""
    if transcription_file.exists():
        transcription_text = transcription_file.read_text(encoding="utf-8")
    else:
        # Attempt Gemma transcription; fall back to sample lyrics on failure
        try:
            gemma_processor = get_processor("gemma_3n")
            result = gemma_processor.process(
                file_id,
                test_file,
                model_variant="gemma-2-2b",
                task="transcribe",
            )
            transcription_text = result.get("analysis_summary", "")
        except Exception:
            transcription_text = (
                "This is a sample song lyrics\n"
                "For testing karaoke generation\n"
                "With multiple lines of text\n"
                "That will be synced with music\n"
            )

    karaoke_processor = get_processor("karaoke")
    result = karaoke_processor.process(
        file_id,
        instrumental_file,
        vocals_file or str(test_file),
        transcription_text,
        original_audio_path=str(test_file),
    )

    assert isinstance(result, dict)
    assert result.get("lrc_file") and result.get("karaoke_dir")
