"""Quick test script for whisper_loader.get_preferred_device

Run locally to verify device selection logic without importing whisper.

Examples:
  # dry-run uses env vars
  python test_whisper_loader.py --dry-run

  # force GPU via env
  setx WHISPER_FORCE_GPU 1
  python test_whisper_loader.py --dry-run

  # or via CLI override
  python test_whisper_loader.py --force-gpu --dry-run
"""
from __future__ import annotations

import os
import argparse

from whisper_loader import get_preferred_device, load_whisper_model


def _cli():
    parser = argparse.ArgumentParser(
        description="Test whisper loader device selection"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't load model; just show chosen device",
    )
    parser.add_argument(
        "--force-gpu",
        action="store_true",
        help="Temporarily force GPU for this run",
    )
    parser.add_argument(
        "--cuda-device",
        help="CUDA device index or string (e.g. 0 or cuda:1)",
    )
    parser.add_argument(
        "--model-dir",
        help="Model dir or name (optional)",
    )
    args = parser.parse_args()

    if args.force_gpu:
        os.environ["WHISPER_FORCE_GPU"] = "1"
    if args.cuda_device:
        os.environ["WHISPER_CUDA_DEVICE"] = args.cuda_device

    device = get_preferred_device(
        os.environ.get("WHISPER_FORCE_GPU"),
        os.environ.get("WHISPER_CUDA_DEVICE"),
    )
    print(f"Chosen device: {device}")

    if args.dry_run:
        print("Dry run complete")
        return

    # Try to actually load (may be slow/heavy). Use small default if not given.
    model_dir = args.model_dir or "small"
    print(f"Attempting to load model {model_dir} on device {device}")
    m = load_whisper_model(model_dir, device=device, dry_run=False)
    print(f"Loaded model: {type(m)}")


if __name__ == '__main__':
    _cli()
