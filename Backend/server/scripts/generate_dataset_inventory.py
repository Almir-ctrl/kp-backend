#!/usr/bin/env python3
"""Generate dataset inventory for Whisper training.

Scans `uploads/` and `outputs/` for audio files, computes size and SHA256, attempts to read duration via ffprobe if available, detects transcripts, and writes:
- manifests/dataset_inventory.csv
- manifests/dataset_inventory_summary.json

Usage: python server/scripts/generate_dataset_inventory.py
"""
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPLOADS = ROOT / 'uploads'
OUTPUTS = ROOT / 'outputs'
MANIFESTS = ROOT / 'manifests'

EXTS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac', '.wav', '.opus'}


def find_audio_files(paths):
    for base in paths:
        if not base.exists():
            continue
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                if Path(fn).suffix.lower() in EXTS:
                    yield Path(dirpath) / fn


def sha256_file(path, block_size=65536):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                h.update(block)
    except Exception:
        return None
    return h.hexdigest()


def get_duration_ffprobe(path):
    try:
        # ffprobe example:
        # ffprobe -v error -show_entries format=duration \
        #   -of default=noprint_wrappers=1:nokey=1 file
        p = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        out = p.stdout.strip()
        if out:
            return float(out)
    except Exception:
        return None
    return None


def simple_language_guess(filename: str):
    s = filename.lower()
    if any(x in s for x in ['bos', 'bs', 'bosnian', 'bosanski']):
        return 'bs'
    if any(x in s for x in ['hr', 'hrv', 'cro', 'croatian', 'hrvatski']):
        return 'hr'
    if any(x in s for x in ['sr', 'srb', 'srpski', 'serb']):
        return 'sr'
    return ''


def find_transcript(path: Path):
    # check same dir for .txt/.json
    for ext in ('.txt', '.norm.txt', '.json'):
        p = path.with_suffix(ext)
        if p.exists():
            return str(p)

    # check outputs/<basename>/transcription_base.txt or .json
    candidate = OUTPUTS / path.stem / 'transcription_base.txt'
    if candidate.exists():
        return str(candidate)

    candidatej = OUTPUTS / path.stem / 'transcription_base.json'
    if candidatej.exists():
        return str(candidatej)

    return ''


def ensure_manifests_dir():
    MANIFESTS.mkdir(parents=True, exist_ok=True)


def main():
    ensure_manifests_dir()
    files = list(find_audio_files([UPLOADS, OUTPUTS]))
    print(f'Found {len(files)} audio files to inventory.')

    rows = []
    hash_map = {}
    unreadable = []

    ffprobe_available = shutil.which('ffprobe') is not None
    if not ffprobe_available:
        print('ffprobe not found in PATH — durations will be blank.')

    for p in files:
        try:
            size = p.stat().st_size
        except Exception:
            size = ''
        duration = None
        if ffprobe_available:
            duration = get_duration_ffprobe(p)
        file_hash = sha256_file(p)
        if file_hash is None:
            unreadable.append(str(p))
        duplicate = False
        if file_hash:
            if file_hash in hash_map:
                duplicate = True
            else:
                hash_map[file_hash] = str(p)

        transcript = find_transcript(p)
        lang = simple_language_guess(p.name)

        rows.append({
            'filename': p.name,
            'path': str(p.relative_to(ROOT)),
            'size_bytes': size,
            'duration_seconds': '' if duration is None else round(duration, 3),
            'sha256': file_hash or '',
            'transcript_path': transcript,
            'language_guess': lang,
            'duplicate': duplicate,
        })

    csv_path = MANIFESTS / 'dataset_inventory.csv'
    json_summary = MANIFESTS / 'dataset_inventory_summary.json'

    fieldnames = [
        'filename',
        'path',
        'size_bytes',
        'duration_seconds',
        'sha256',
        'transcript_path',
        'language_guess',
        'duplicate',
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    total_bytes = sum(
        r['size_bytes'] for r in rows if isinstance(r['size_bytes'], int)
    )
    duplicates_found = sum(1 for r in rows if r['duplicate'])

    summary = {
        'total_files': len(rows),
        'total_bytes': total_bytes,
        'unreadable_files': unreadable,
        'duplicates_found': duplicates_found,
        'ffprobe_available': ffprobe_available,
    }

    with open(json_summary, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f'Wrote CSV: {csv_path}')
    print(f'Wrote summary: {json_summary}')


if __name__ == '__main__':
    main()
