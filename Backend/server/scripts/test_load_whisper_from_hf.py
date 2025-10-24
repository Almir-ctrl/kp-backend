"""Download a Hugging Face Whisper model snapshot to the repo and
try loading it.

Usage (PowerShell):
    $env:HF_TOKEN = '<your token>'
    $env:WHISPER_MODEL_REPO = 'openai/whisper-large-v2'
    python server/scripts/test_load_whisper_from_hf.py

This script re-uses the project's hf_downloader_factory to copy the
HF snapshot into `models/whisper/<sanitized-repo>` and then attempts to
call `whisper.load_model(local_dir)`. It prints diagnostics and returns
exit code 0 on success, non-zero on failure.
"""
import os
import sys
from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Download HF whisper model and try loading'
    )
    parser.add_argument(
        '--repo',
        help='HF repo id (e.g. openai/whisper-large-v2)',
        default=None,
    )
    parser.add_argument(
        '--model-size',
        help='Fallback model name (tiny/base/etc.)',
        default='base',
    )
    args = parser.parse_args()

    repo = args.repo or os.environ.get('WHISPER_MODEL_REPO')
    if not repo:
        print(
            'Error: no HF repo specified. Set --repo or '
            'WHISPER_MODEL_REPO env var.'
        )
        return 2

    # Ensure project root on path
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        from server.scripts.download_whisper_model import (
            hf_downloader_factory,
            model_dir_for,
        )
    except Exception as e:
        print('Failed to import downloader helper:', e)
        return 3

    print('Using HF repo:', repo)

    downloader = hf_downloader_factory(repo)
    local_dir = model_dir_for(repo)
    print('Destination local model dir:', local_dir)

    try:
        ok = downloader(repo, local_dir)
        if not ok:
            print('Downloader reported failure')
            return 4
    except Exception as e:
        print('Downloader raised exception:', e)
        return 5

    print('Snapshot copied to', local_dir)

    # Attempt to load with whisper
    try:
        import whisper
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print('Attempting to load whisper model from local dir on', device)
        # whisper.load_model accepts either a model name or a path. The
        # whisper implementation may expect a checkpoint file path rather
        # than the directory, so try a few common checkpoint filenames.
        tried = []
        checkpoint_candidates = [
            local_dir / 'model.pt',
            local_dir / 'pytorch_model.bin',
            local_dir / 'model.safetensors',
        ]

        m = None
        # First try the directory (some whisper versions accept it)
        tried.append(str(local_dir))
        try:
            m = whisper.load_model(str(local_dir), device=device)
        except Exception:
            m = None

        if m is None:
            for c in checkpoint_candidates:
                tried.append(str(c))
                if c.exists():
                    try:
                        m = whisper.load_model(str(c), device=device)
                        break
                    except Exception:
                        m = None
            if m is None:
                print('whisper.load_model returned None')
                print('Tried paths:', tried)

                # Check for tokenizer artifacts and warn if missing
                tokenizer_files = [
                    'tokenizer.json', 'tokenizer_config.json', 'vocab.json',
                    'merges.txt', 'tokenizer.model', 'spiece.model'
                ]
                missing = []
                for t in tokenizer_files:
                    if not (local_dir / t).exists():
                        missing.append(t)
                if missing:
                    print(
                        'Warning: tokenizer artifacts appear missing:',
                        missing,
                    )
                return 6
        print('Success: whisper.load_model returned a model object')
        return 0
    except Exception as e:
        print('Failed to load whisper from local dir:', e)
        import traceback
        traceback.print_exc()
        print('\nAs a fallback, try loading the named model size instead:')
        print(f"  whisper.load_model('{args.model_size}')")
        return 7


if __name__ == '__main__':
    sys.exit(main())
