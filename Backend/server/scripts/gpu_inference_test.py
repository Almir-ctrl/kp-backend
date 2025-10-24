"""Run a small GPU inference test using the converted whisper model.

This script:
- creates a 1s 440Hz sine WAV in the OS temp dir
- loads the model via whisper_loader.load_whisper_model
    (honors WHISPER_FORCE_GPU)
- runs model.transcribe on the audio and prints timing
- prints torch.cuda memory stats when available

Use with caution: will import torch and whisper and may use GPU memory.
"""
from __future__ import annotations

import os
import time
import tempfile
import argparse
import math

try:
    import torch
except Exception:
    torch = None

import soundfile as sf

from whisper_loader import load_whisper_model, get_preferred_device


def generate_sine_wav(
    path: str, duration: float = 1.0, sr: int = 16000, freq: float = 440.0
):
    samples = int(duration * sr)
    data = [math.sin(2 * math.pi * freq * (i / sr)) for i in range(samples)]
    sf.write(path, data, sr, subtype='PCM_16')


def main(model_dir: str, dry_run: bool = False):
    tmpdir = tempfile.gettempdir()
    wav_path = os.path.join(tmpdir, 'whisper_test_sine.wav')
    print(f"Generating test WAV: {wav_path}")
    generate_sine_wav(wav_path)

    device = get_preferred_device(
        os.environ.get('WHISPER_FORCE_GPU'),
        os.environ.get('WHISPER_CUDA_DEVICE'),
    )
    print(f"Preferred device (before load): {device}")

    if dry_run:
        print("Dry run: not loading model")
        return

    t0 = time.time()
    model = load_whisper_model(model_dir, device=None, dry_run=False)
    load_time = time.time() - t0
    print(f"Model loaded in {load_time:.2f}s")

    if torch is not None and torch.cuda.is_available():
        print(
            f"CUDA devices: {torch.cuda.device_count()}, "
            f"current: {torch.cuda.current_device()}"
        )
        try:
            alloc_mb = torch.cuda.memory_allocated() / (1024**2)
            print(f"Allocated: {alloc_mb:.1f} MB")
        except Exception:
            pass

    # Run transcription
    if not hasattr(model, 'transcribe'):
        raise RuntimeError('Loaded model has no transcribe() method')

    t1 = time.time()
    result = model.transcribe(wav_path)
    t2 = time.time()
    print(f"Transcription time: {t2 - t1:.2f}s")
    if isinstance(result, dict):
        print("Result text:", result.get('text'))
    else:
        print("Result:")
        print(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='GPU inference test for whisper'
    )
    parser.add_argument(
        '--model-dir',
        required=True,
        help='Path to whisper model dir or checkpoint',
    )
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(args.model_dir, dry_run=args.dry_run)
