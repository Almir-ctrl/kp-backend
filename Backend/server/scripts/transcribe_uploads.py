#!/usr/bin/env python
"""Transcribe the newest audio file in uploads/ using the converted
Whisper checkpoint.

Usage:
    python transcribe_uploads.py [--model <path-to-pt>] [--use-gpu]
"""
from pathlib import Path
import argparse
import sys


def find_latest_upload():
    up = Path(__file__).resolve().parents[2] / 'uploads'
    files = [
        p
        for p in up.iterdir()
        if p.is_file() and (
            p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac')
        )
    ]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--model', help='Path to converted whisper .pt', default=None
    )
    parser.add_argument('--use-gpu', action='store_true')
    args = parser.parse_args()

    song = find_latest_upload()
    if not song:
        print('No audio files found in uploads/. Add one and retry.')
        return 2

    print('Found file:', song)

    # discover default model location if not provided
    if args.model:
        model_path = Path(args.model)
    else:
        model_path = (
            Path(__file__).resolve().parents[2]
            / 'models'
            / 'whisper'
            / 'openai_whisper-large-v2'
            / 'model_converted.pt'
        )

    if not model_path.exists():
        print('Converted model not found at', model_path)
        return 3

    # load loader if available
    loader_path = Path(__file__).parent / 'whisper_loader.py'
    device = 'cpu'
    if args.use_gpu:
        # allow loader to pick preferred device
        if loader_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'whisper_loader', str(loader_path)
            )
            if spec is not None and spec.loader is not None:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                device = mod.get_preferred_device()
        else:
            device = 'cuda:0'

    print('Using device:', device)
    try:
        import whisper
    except Exception as e:
        print('whisper not available:', e)
        return 4

    print('Loading model...')
    # Prefer using the whisper_loader helper if present — it normalizes CUDA
    # device indices and retries mapped loads on CPU if needed.
    loader_path = Path(__file__).parent / 'whisper_loader.py'
    if loader_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'whisper_loader', str(loader_path)
        )
        if spec is not None and spec.loader is not None:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            try:
                model = mod.load_whisper_model(str(model_path), device=device)
            except Exception:
                # Fall back to direct whisper.load_model if loader helper fails
                model = whisper.load_model(str(model_path), device=device)
        else:
            model = whisper.load_model(str(model_path), device=device)
    else:
        model = whisper.load_model(str(model_path), device=device)
    print('Transcribing...')
    res = model.transcribe(str(song))
    print('\nTranscription result:')
    print(res.get('text', ''))
    # Prepare outputs directory
    out_base = Path(__file__).resolve().parents[2] / 'outputs'
    slug = song.stem.replace(' ', '_')
    out_dir = out_base / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write full text
    text_val = res.get('text', '') if isinstance(res, dict) else ''
    if not isinstance(text_val, str):
        text_val = str(text_val)
    (out_dir / 'transcription_base.txt').write_text(text_val, encoding='utf-8')

    # Write JSON with segments
    import json
    (out_dir / 'transcription_base.json').write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding='utf-8'
    )

    # Write simple karaoke LRC using segment start times
    def fmt_ts(s):
        # format seconds to [mm:ss.xx]
        m = int(s // 60)
        sec = s - m * 60
        return f"[{m:02d}:{sec:05.2f}]"

    lrc_lines = []
    segments = res.get('segments', []) if isinstance(res, dict) else []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        start = seg.get('start', 0.0)
        text = seg.get('text', '')
        if not isinstance(text, str):
            text = str(text)
        lrc_lines.append(f"{fmt_ts(start)}{text.strip()}")
    karaoke_path = out_dir / 'karaoke.lrc'
    karaoke_path.write_text('\n'.join(lrc_lines), encoding='utf-8')

    # Write metadata
    duration = None
    if segments:
        last = segments[-1]
        if isinstance(last, dict):
            duration = last.get('end')
    metadata = {
        'original_filename': song.name,
        'duration': duration,
    }
    (out_dir / 'metadata.json').write_text(
        json.dumps(metadata, indent=2), encoding='utf-8'
    )

    print('\nWrote outputs to:', out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
