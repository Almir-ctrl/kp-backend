"""Minimal Whisper training runner for AiMusicSeparator-Backend.

This script implements a mock-capable training entrypoint suitable for CI
smoke tests and local runs. It supports a ``--mock-model`` flag which avoids
heavy ML dependencies and a ``--fast-dev-run`` to perform a tiny quick loop.

Usage example:

    python server/scripts/train_whisper.py \
        --out-dir models/whisper/mock --mock-model --fast-dev-run

The script creates the output directory and writes small checkpoint-like files
and a ``metrics.json`` to simulate a successful run.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Train/fine-tune a Whisper-style model (mock-capable)"
        )
    )
    p.add_argument(
        "--out-dir",
        default="models/whisper/mock-run",
        help="Where to write model artifacts",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Number of training steps to run (mock)",
    )
    p.add_argument(
        "--fast-dev-run",
        action="store_true",
        help="Run a very short dev smoke loop",
    )
    p.add_argument(
        "--mock-model",
        action="store_true",
        help=(
            "Run in mock mode without torch/transformers"
        ),
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    return p.parse_args()


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def write_mock_checkpoint(out_dir: Path, step: int):
    ckpt = {
        "checkpoint_step": step,
        "model_name": "mock-whisper",
        "created_at": time.time(),
    }
    with open(out_dir / f"checkpoint-{step}.json", "w", encoding="utf-8") as f:
        json.dump(ckpt, f)


def write_metrics(out_dir: Path, loss_history):
    metrics = {
        "loss": loss_history,
        "final_loss": loss_history[-1] if loss_history else None,
        "steps": len(loss_history),
    }
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f)


def run_mock_training(
    out_dir: Path, max_steps: int, fast_dev: bool, seed: int
):
    random.seed(seed)
    loss_history = []
    steps = 2 if fast_dev else max_steps
    for step in range(1, steps + 1):
        # Simulate some work
        time.sleep(0.01 if fast_dev else 0.05)
        loss = max(0.0, 2.0 * (0.9 ** step) + random.random() * 0.01)
        loss_history.append(loss)
        # write a tiny checkpoint every step
        write_mock_checkpoint(out_dir, step)
    write_metrics(out_dir, loss_history)
    print("[mock] Training finished. Steps=", steps)
    print("Artifacts in:", out_dir)


def try_real_training(
    out_dir: Path, max_steps: int, fast_dev: bool, seed: int
):
    # Try to import torch; if missing, raise ImportError to fallback to mock
    try:
        import torch  # type: ignore
    except Exception as e:
        raise ImportError("PyTorch not available: " + str(e))

    # Minimal real loop that doesn't allocate big models. Create a tiny tensor
    # and run a fake optimizer step.
    torch.manual_seed(seed)
    loss_history = []
    steps = 2 if fast_dev else max_steps
    # tiny model: a single linear weight
    w = torch.randn(1, requires_grad=True)
    opt = torch.optim.SGD([w], lr=0.1)
    for step in range(1, steps + 1):
        opt.zero_grad()
        # fake loss: (w - target)^2
        target = torch.tensor([0.0])
        loss = (w - target).pow(2).sum()
        loss.backward()
        opt.step()
        loss_val = float(loss.detach().cpu().numpy())
        loss_history.append(loss_val)
        write_mock_checkpoint(out_dir, step)
    write_metrics(out_dir, loss_history)
    print("[real] Tiny training finished. Steps=", steps)
    print("Artifacts in:", out_dir)


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    if args.mock_model:
        run_mock_training(
            out_dir, args.max_steps, args.fast_dev_run, args.seed
        )
        return

    # Try real training; fall back to mock if dependencies missing
    try:
        try_real_training(
            out_dir, args.max_steps, args.fast_dev_run, args.seed
        )
    except ImportError as e:
        print("Real training dependencies missing:", e)
        print(
            "Falling back to mock training. To run real training, install "
            "PyTorch and optional transformers."
        )
        run_mock_training(
            out_dir, args.max_steps, args.fast_dev_run, args.seed
        )


if __name__ == "__main__":
    main()
