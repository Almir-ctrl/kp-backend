#!/usr/bin/env python3
"""Normalize transcripts for Whisper training.

This script reads `manifests/dataset_inventory.csv`, finds `transcript_path`
entries and writes a normalized version alongside the original transcript as
`<name>.norm.txt`. A summary is written to
`manifests/normalize_summary.json`.

Normalization performed (lightweight):
- Unicode NFC normalization
- Remove bracketed annotations like [laughs], (music), {applause}
- Replace common fancy quotes/dashes
- Collapse whitespace and trim
"""
from pathlib import Path
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / 'manifests'
MANIFESTS.mkdir(parents=True, exist_ok=True)

BRACKET_RE = re.compile(r"\[[^\]]*\]|\([^\)]*\)|\{[^}]*\}")
WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    t = unicodedata.normalize('NFC', text)
    t = BRACKET_RE.sub(' ', t)
    t = t.replace('\u2019', "'")
    t = t.replace('\u201c', '"').replace('\u201d', '"')
    t = t.replace('\u2013', '-').replace('\u2014', '-')
    t = WS_RE.sub(' ', t)
    return t.strip()


def main():
    csv_path = MANIFESTS / 'dataset_inventory.csv'
    if not csv_path.exists():
        raise FileNotFoundError('Run generate_dataset_inventory.py first')

    import csv
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)

    summary = {'processed': 0, 'written': 0, 'missing': []}

    for r in rows:
        transcript = r.get('transcript_path')
        if not transcript:
            summary['missing'].append(r.get('path'))
            continue
        tpath = ROOT / transcript
        if not tpath.exists():
            summary['missing'].append(str(tpath))
            continue
        try:
            s = tpath.read_text(encoding='utf-8')
        except Exception:
            try:
                s = tpath.read_text(encoding='latin-1')
            except Exception:
                summary['missing'].append(str(tpath))
                continue
        norm = normalize_text(s)
        out = tpath.with_suffix(tpath.suffix + '.norm.txt')
        out.write_text(norm, encoding='utf-8')
        summary['processed'] += 1
        summary['written'] += 1

    out_file = MANIFESTS / 'normalize_summary.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'Wrote normalization summary: {out_file}')


if __name__ == '__main__':
    main()
