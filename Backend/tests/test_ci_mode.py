import os
import pytest
from pathlib import Path

# Mark the whole module as CI smoke tests so CI can run just these via -m ci_smoke
pytestmark = pytest.mark.ci_smoke


def test_whisper_ci_mock_writes_outputs(tmp_path, monkeypatch):
    # Enable CI mode
    monkeypatch.setenv("CI_SMOKE", "true")

    # Ensure project is importable
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    from app import app
    from models import WhisperManager

    # Run inside Flask app context so current_app.config is available
    with app.app_context():
        wm = WhisperManager()
        out = wm.transcribe(
            "test-ci-whisper",
            str(repo_root / "tests" / "fixtures" / "sample.wav"),
            "base",
        )

        assert isinstance(out, dict)
        assert out.get("text") == "(ci-mock) transcription"

        # Ensure files were created under outputs/test-ci-whisper
        out_dir = Path(app.config["OUTPUT_FOLDER"]) / "test-ci-whisper"
        assert out_dir.exists()
        assert (out_dir / out["files"]["text"]).exists()


def test_musicgen_ci_uses_mock(monkeypatch):
    monkeypatch.setenv("CI_SMOKE", "true")

    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    from app import app
    from models import MusicGenProcessor

    # Instantiate and run inside the Flask app context so current_app is available
    with app.app_context():
        proc = MusicGenProcessor("musicgen")
        result = proc.process(
            "test-ci-musicgen",
            "tests/fixtures/sample.wav",
            model_variant="small",
            prompt="ci mock prompt",
        )

    assert isinstance(result, dict)
    assert "generated_file" in result or "prompt_file" in result


def test_gemma3n_ci_returns_synthetic(monkeypatch):
    monkeypatch.setenv("CI_SMOKE", "true")

    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    from app import app
    from models import Gemma3NProcessor

    # Instantiate inside the Flask app context
    with app.app_context():
        # Processor expects the model key (as in config), pass the variant
        proc = Gemma3NProcessor("gemma_3n")
        res = proc.process(
            "test-ci-gemma",
            "tests/fixtures/sample.wav",
            model_variant="gemma-2-9b-it",
            task="analyze",
        )

    assert isinstance(res, dict)
    assert "analysis" in res
