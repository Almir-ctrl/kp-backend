"""Safe smoke trainer for Whisper-style fine-tuning.

This script attempts to run a tiny HF-style training loop if
`transformers` and `datasets` are installed. If not available it
falls back to a mock trainer that writes a minimal checkpoint and
metadata into `models/whisper/smoke-run/` so downstream tooling can
verify artifact presence.

Usage:
    python server/scripts/train_whisper_hf_smoke.py \
            --manifest manifests/run1_processed.jsonl

This script is intentionally safe for CPU-only environments and will
never download large model weights by default.
"""
from pathlib import Path
import argparse
import json
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "models" / "whisper" / "smoke-run"
OUT.mkdir(parents=True, exist_ok=True)


def mock_trainer(manifest: Path, steps: int = 1):
    """Create a tiny mock checkpoint and metadata file."""
    # read manifest count
    n = 0
    if manifest.exists():
        with manifest.open("r", encoding="utf-8") as fh:
            for _ in fh:
                n += 1

    metadata = {
        "mode": "mock",
        "manifest": str(manifest),
        "items": n,
        "steps": steps,
        "timestamp": time.time(),
    }
    (OUT / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    # create a tiny checkpoint file
    ckpt = {"step": steps, "loss": 0.0}
    try:
        import torch

        torch.save(ckpt, str(OUT / "pytorch_model.bin"))
        print("Wrote mock PyTorch checkpoint:", OUT / "pytorch_model.bin")
    except Exception:
        # fallback: write json
        (OUT / "pytorch_model.bin.json").write_text(
            json.dumps(ckpt), encoding="utf-8"
        )
        print("Wrote mock JSON checkpoint:", OUT / "pytorch_model.bin.json")

    print(
        "Mock training complete. Metadata written to:", OUT / "metadata.json"
    )


def hf_smoke_trainer(manifest: Path, steps: int = 1):
    """Attempt a minimal HF-style setup. Will not download large models.

    This path only runs if `transformers` and `datasets` are importable.
    It creates a tiny tokenizer & config and saves them to the output dir.
    """
    from transformers import AutoConfig, AutoTokenizer

    # create a minimal config and tokenizer (no weights)
    cfg = AutoConfig.from_pretrained(
        "openai/whisper-small", trust_remote_code=False
    )
    tokenizer = AutoTokenizer.from_pretrained(
        "openai/whisper-small", trust_remote_code=False
    )

    cfg.save_pretrained(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    # write tiny metadata
    meta = {
        "mode": "hf",
        "manifest": str(manifest),
        "steps": steps,
        "timestamp": time.time(),
    }
    (OUT / "metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print("Saved HF tokenizer/config to:", OUT)


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--manifest",
        default=str(ROOT / "manifests" / "run1_processed.jsonl"),
    )
    p.add_argument("--steps", type=int, default=1)
    args = p.parse_args()
    manifest = Path(args.manifest)

    # Try HF path: import transformers and datasets if available
    try:
        import importlib

        importlib.import_module("transformers")
        # try loading datasets module; if it's missing we'll fall back
        try:
            importlib.import_module("datasets")
            has_datasets = True
        except Exception:
            has_datasets = False

        if has_datasets:
            print("transformers + datasets available — attempting HF path")
            hf_smoke_trainer(manifest, steps=args.steps)
        else:
            print("datasets module not available — running mock trainer")
            mock_trainer(manifest, steps=args.steps)
    except Exception:
        print("transformers not available — running mock trainer")
        mock_trainer(manifest, steps=args.steps)


if __name__ == "__main__":
    main()
