"""Test Whisper integration (assertion-based)."""
import whisper


def test_whisper():
    # List available models (ensure API exists)
    available_models = whisper.available_models()
    assert isinstance(available_models, (list, tuple))

    # Try to load the tiny model (may raise if dependencies missing)
    model = whisper.load_model("tiny")
    assert model is not None
