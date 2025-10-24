#!/usr/bin/env python
"""Download a HF Transformers Whisper-style model and processor and save
them into the repo under models/whisper/<sanitized-repo> so local loading
via AutoProcessor.from_pretrained(local_dir) and
AutoModelForSpeechSeq2Seq.from_pretrained(local_dir) works.

Usage (PowerShell):
    $env:HF_TOKEN = '<token>'  # optional if repo is public
    python server/scripts/download_whisper_transformers.py \
        --repo openai/whisper-large-v2
"""
from pathlib import Path
import argparse
import os
import sys


def model_dir_for(name: str) -> Path:
    safe = name.replace('/', '_').replace(':', '_')
    return Path(__file__).resolve().parents[2] / 'models' / 'whisper' / safe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--repo',
        default=os.environ.get(
            'WHISPER_MODEL_REPO', 'openai/whisper-large-v2'
        ),
    )
    args = parser.parse_args()
    repo = args.repo

    dest = model_dir_for(repo)
    dest.mkdir(parents=True, exist_ok=True)

    print('Downloading processor and model for', repo)
    # Import here to fail fast if transformers is missing
    try:
        from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
    except Exception as e:
        print('Failed to import transformers:', e)
        sys.exit(2)

    # Allow use of HF_TOKEN env var for private repos
    token = os.environ.get('HF_TOKEN')
    kwargs = {}
    if token:
        kwargs['use_auth_token'] = token

    try:
        print('Loading processor...')
        processor = AutoProcessor.from_pretrained(repo, **kwargs)
        print('Saving processor to', dest)
        processor.save_pretrained(dest)
    except Exception as e:
        print('Processor download/save failed:', e)
        raise

    try:
        print('Loading model...')
        model = AutoModelForSpeechSeq2Seq.from_pretrained(repo, **kwargs)
        print('Saving model to', dest)
        model.save_pretrained(dest)
    except Exception as e:
        print('Model download/save failed:', e)
        raise

    print('Download complete. Local model dir:', dest)


if __name__ == '__main__':
    main()
