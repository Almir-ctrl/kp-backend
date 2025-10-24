#!/usr/bin/env python
"""Transcribe the newest audio file in uploads/ using Hugging Face Transformers
and the local model files under `models/whisper/openai_whisper-large-v2/`.

This acts as a second transcription path using the Transformers HF model
and processor (AutoProcessor + AutoModelForSpeechSeq2Seq) to compare with
converted Whisper checkpoint results.

Usage:
    python transcribe_with_transformers.py [--use-gpu]
"""
from pathlib import Path
import argparse
import sys
import json


def find_latest_upload():
    up = Path(__file__).resolve().parents[2] / 'uploads'
    files = [
        p
        for p in up.iterdir()
        if p.is_file()
        and p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac')
    ]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-gpu', action='store_true')
    args = parser.parse_args()

    song = find_latest_upload()
    if not song:
        print('No audio files found in uploads/. Add one and retry.')
        return 2

    print('Found file:', song)

    model_dir = (
        Path(__file__).resolve().parents[2]
        / 'models'
        / 'whisper'
        / 'openai_whisper-large-v2'
    )

    if not model_dir.exists():
        print('Local transformers model dir not found at', model_dir)
        return 3

    device = 'cpu'
    if args.use_gpu:
        try:
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
        except Exception:
            device = 'cpu'

    print('Using device for transformers:', device)

    try:
        from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
        import soundfile as sf
        import torch
    except Exception as e:
        print('Missing dependencies for transformers transcription:', e)
        return 4

    print('Loading processor and model from', model_dir)
    processor = AutoProcessor.from_pretrained(str(model_dir))
    model = AutoModelForSpeechSeq2Seq.from_pretrained(str(model_dir))
    model.to(device)
    model.eval()

    # Read audio
    wav, sr = sf.read(str(song))
    if sr != 16000:
        print(
            'Warning: input sample rate != 16000 Hz, resampling to 16000'
            ' will be performed'
        )
        # Try scipy resample for performance. If not available, try librosa.
        # Fallback to a chunked numpy interpolation to avoid large memory or
        # blocking issues on long audio files.
        resampled = None
        try:
            from scipy.signal import resample as scipy_resample

            import numpy as np

            if wav.ndim > 1:
                wav_mono = np.mean(wav, axis=1)
            else:
                wav_mono = wav
            orig_len = wav_mono.shape[0]
            new_len = int(orig_len * 16000 / sr)
            res_tmp = scipy_resample(wav_mono, new_len)
            import numpy as np
            resampled = np.asarray(res_tmp).astype('float32')
            wav = resampled
            sr = 16000
        except Exception:
            try:
                import librosa

                wav = librosa.resample(
                    wav.astype('float32'), orig_sr=sr, target_sr=16000
                )
                sr = 16000
            except Exception:
                # Chunked numpy interpolation fallback (memory-friendly)
                import numpy as np

                if wav.ndim > 1:
                    wav = np.mean(wav, axis=1)
                orig_len = wav.shape[0]
                new_len = int(orig_len * 16000 / sr)
                # Avoid large temporary arrays by working in chunks
                chunk = 10_000_000  # ~10M samples per chunk
                if orig_len <= chunk:
                    orig_times = np.linspace(0, orig_len / sr, orig_len)
                    new_times = np.linspace(0, orig_len / sr, new_len)
                    tmp = np.interp(new_times, orig_times, wav)
                    wav = tmp.astype('float32')
                else:
                    # Build output by chunking input
                    out = np.empty(new_len, dtype='float32')
                    for i in range(0, orig_len, chunk):
                        start = i
                        end = min(orig_len, i + chunk)
                        seg = wav[start:end]
                        orig_times = np.linspace(
                            start / sr, end / sr, seg.shape[0]
                        )
                        # Map output indices that fall into this segment
                        out_start = int(start * 16000 / sr)
                        out_end = int(end * 16000 / sr)
                        if out_end > out_start:
                            new_times = np.linspace(
                                start / sr, end / sr, out_end - out_start
                            )
                            part = np.interp(new_times, orig_times, seg)
                            out[out_start:out_end] = part
                    wav = out
                sr = 16000

    # Processor expects float32 numpy array
    import numpy as np
    if wav.ndim > 1:
        # Convert multi-channel to mono by averaging
        wav = np.mean(wav, axis=1)
    if wav.dtype != np.float32:
        wav = wav.astype(np.float32)

    inputs = processor(wav, sampling_rate=16000, return_tensors="pt")
    input_values = (
        inputs.get('input_features')
        or inputs.get('input_values')
        or inputs['input_features']
    )

    input_values = input_values.to(device)

    with torch.no_grad():
        generated_ids = model.generate(
            input_values=input_values, max_new_tokens=512
        )
        # decode with processor
        transcription = processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]

    print('\nTransformers transcription:')
    print(transcription)

    # Write result next to other outputs for comparison
    out_base = Path(__file__).resolve().parents[2] / 'outputs'
    slug = song.stem.replace(' ', '_') + '_transformers'
    out_dir = out_base / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / 'transcription_transformers.txt').write_text(
        transcription, encoding='utf-8'
    )
    (out_dir / 'transcription_transformers.json').write_text(
        json.dumps({'text': transcription}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    print('\nWrote transformers outputs to:', out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
