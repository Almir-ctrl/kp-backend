#!/usr/bin/env python
"""Inspect transformers AutoModelForSpeechSeq2Seq state dict keys.

Usage: python inspect_transformers_state.py --local-dir <path>
Prints a small sample of keys and a histogram of common substrings to aid
in writing deterministic mapping rules for the converter.
"""
from pathlib import Path
import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-dir', required=True)
    args = parser.parse_args()
    local = Path(args.local_dir)
    if not local.exists():
        print('Local dir not found:', local)
        return 2

    try:
        from transformers import AutoModelForSpeechSeq2Seq
    except Exception as e:
        print('transformers not available:', e)
        return 3

    print('Loading transformers model from', local)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(str(local))
    keys = list(model.state_dict().keys())
    print('Total transformer state keys:', len(keys))
    print('\nSample keys (first 120):')
    for k in keys[:120]:
        print(' ', k)

    # gather substrings frequency for parts separated by '.'
    from collections import Counter

    parts = []
    for k in keys:
        parts.extend(k.split('.'))
    c = Counter(parts)
    print('\nMost common token parts:')
    for tok, cnt in c.most_common(60)[:60]:
        print(f'  {tok}: {cnt}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
