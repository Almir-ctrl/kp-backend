"""Small preprocessing helper for Whisper training.

This script validates audio files (mock-capable), optionally rescales or
resamples them, and writes a simple manifest JSONL file suitable for the
training runner. For CI we support --mock which creates a tiny fake dataset.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(
        description="Preprocess audio for Whisper training"
    )
    p.add_argument("--out-manifest", default="manifests/run1.jsonl")
    p.add_argument("--mock", action="store_true")
    p.add_argument(
        "--count",
        type=int,
        default=2,
        help="Number of mock samples to write",
    )
    return p.parse_args()


def ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def write_mock_manifest(path: Path, count: int):
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        for i in range(count):
            rec = {
                "id": f"mock-{i}",
                "audio": f"data/mock-{i}.wav",
                "duration": 1.23,
                "text": "hello world",
            }
            f.write(json.dumps(rec) + "\n")
    print("Wrote mock manifest:", path)


def main():
    args = parse_args()
    out = Path(args.out_manifest)
    if args.mock:
        write_mock_manifest(out, args.count)
        return

    # Real preprocessing not implemented; write a helpful message.
    print("Real preprocessing not implemented in this helper.")
    print("You can use --mock to generate a small manifest for CI tests.")


if __name__ == "__main__":
    main()
