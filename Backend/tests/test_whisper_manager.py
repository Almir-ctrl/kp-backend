import os
import shutil
import numpy as np
import soundfile as sf
import pytest
from flask import Flask

import models


class DummyModel:
    def __init__(self, variant):
        self.variant = variant

    def transcribe(self, path, fp16=True):
        # Return a fake whisper-like dict
        return {
            "model": self.variant,
            "text": "hello world",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "hello world"},
            ],
        }


@pytest.fixture(autouse=True)
def patch_whisper(monkeypatch, tmp_path):
    """Patch WhisperManager._ensure_model and torch.cuda to simulate GPU.

    Also provide a Flask app context with OUTPUT_FOLDER set to tmp_path.
    """

    def fake_ensure(self, variant):
        return DummyModel(variant)

    monkeypatch.setattr(models.WhisperManager, "_ensure_model", fake_ensure, raising=True)

    class FakeCuda:
        @staticmethod
        def is_available():
            return True

    class FakeTorch:
        cuda = FakeCuda()

    monkeypatch.setattr(models, "torch", FakeTorch(), raising=False)

    app = Flask(__name__)
    app.config["OUTPUT_FOLDER"] = str(tmp_path)
    with app.app_context():
        yield


def test_whisper_manager_writes_outputs(tmp_path):
    # Create a tiny wav file
    sr = 16000
    data = np.zeros(int(sr * 0.5), dtype="float32")
    wav_path = tmp_path / "sample.wav"
    sf.write(str(wav_path), data, sr)

    wm = models.WhisperManager()

    out = wm.transcribe(
        file_id="test-file-123", audio_path=str(wav_path), model_variant="small"
    )

    # Check returned structure
    assert out["model"] == "small"
    assert "text" in out and out["text"] == "hello world"
    assert isinstance(out.get("segments"), list)

    # Check files written
    output_dir = out.get("output_dir")
    assert output_dir is not None
    assert os.path.isdir(output_dir)

    json_path = os.path.join(output_dir, out["files"]["json"])
    txt_path = os.path.join(output_dir, out["files"]["text"])

    assert os.path.exists(json_path)
    assert os.path.exists(txt_path)

    # Read text file
    with open(txt_path, "r", encoding="utf-8") as f:
        txt = f.read()
    assert "hello" in txt

    # Cleanup
    shutil.rmtree(output_dir, ignore_errors=True)
