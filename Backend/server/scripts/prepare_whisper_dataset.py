#!/usr/bin/env python3
"""Prepare JSONL manifests for Whisper training.

Creates `manifests/run1_small.jsonl` by selecting up to N samples which have
normalized transcripts (`.norm.txt`). Each line is a JSON object with
fields: id, audio, transcript, duration, language.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / 'manifests'
UPLOADS = ROOT / 'uploads'
MANIFESTS.mkdir(parents=True, exist_ok=True)


def find_pairs(max_items=20):
    pairs = []
    exts = ['.wav', '.mp3', '.m4a']
    for audio in UPLOADS.rglob('*'):
        if audio.suffix.lower() in exts:
            norm = audio.with_suffix('').with_name(audio.stem + '.norm.txt')
            if norm.exists():
                pairs.append((audio, norm))
    return pairs[:max_items]


def write_jsonl(entries, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + '\n')
    print('Wrote', out_path)


def main(max_items=20):
    pairs = find_pairs(max_items)
    entries = []
    for idx, (audio, norm) in enumerate(pairs, start=1):
        text = norm.read_text(encoding='utf-8', errors='ignore')
        entries.append({
            'id': f'run1_{idx}',
            'audio': str(audio.resolve()),
            'transcript': text,
            'duration': None,
        })
    out_path = MANIFESTS / 'run1_small.jsonl'
    write_jsonl(entries, out_path)


if __name__ == '__main__':
    main()
