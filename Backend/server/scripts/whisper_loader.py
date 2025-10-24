"""whisper_loader.py

Utility to load OpenAI/whisper models with an explicit device selection.

The loader respects environment variables so CI/dev can opt into forcing
CUDA when available.

Environment variables:
- WHISPER_FORCE_GPU: if set to 1/true/yes forces attempt to use CUDA.
- WHISPER_CUDA_DEVICE: optional CUDA device index (e.g. "0" or "cuda:1").
"""
from __future__ import annotations

import os
import typing as t
import argparse

try:
    import torch
except Exception:  # pragma: no cover - torch may not be present
    torch = None


def _env_flag_true(val: t.Optional[str]) -> bool:
    if not val:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def get_preferred_device(
    force_gpu_env: t.Optional[str] = None,
    cuda_device_env: t.Optional[str] = None,
) -> str:
    """Decide which device to use for loading inference.

    Args:
        force_gpu_env: value from WHISPER_FORCE_GPU env (string) or None.
        cuda_device_env: value from WHISPER_CUDA_DEVICE env (string) or None.

    Returns:
        device string suitable for passing to whisper.load_model.
    """
    # Default: prefer CPU unless forced and CUDA available
    force_gpu = _env_flag_true(force_gpu_env)
    cuda_spec = (cuda_device_env or os.environ.get("WHISPER_CUDA_DEVICE"))

    if torch is None:
        # If torch isn't importable, fall back to CPU
        return "cpu"

    if force_gpu:
        if torch.cuda.is_available():
            # If an index like "0" or "cuda:1" provided, normalize it.
            if cuda_spec:
                cs = cuda_spec.strip()
                if cs.isdigit():
                    return f"cuda:{cs}"
                if cs.startswith("cuda:"):
                    return cs
                # allow passing full CUDA device string
                return cs
            # Default to generic cuda device
            return "cuda"
        # Forced but not available -> fall back to cpu
        return "cpu"

    # Not forced: prefer CUDA if available
    if torch.cuda.is_available():
        if cuda_spec:
            cs = cuda_spec.strip()
            if cs.isdigit():
                return f"cuda:{cs}"
            if cs.startswith("cuda:"):
                return cs
            return cs
        return "cuda"

    return "cpu"


def load_whisper_model(
    model_dir: str, device: t.Optional[str] = None, dry_run: bool = False
):
    """Load a whisper model from model_dir honoring env vars.

    If dry_run is True, the function will not import whisper or load the
    model; it will just return the chosen device string for verification.
    """
    if device is None:
        device = get_preferred_device(
            os.environ.get("WHISPER_FORCE_GPU"),
            os.environ.get("WHISPER_CUDA_DEVICE"),
        )

    if dry_run:
        return device

    try:
        import whisper
    except Exception as e:
        raise RuntimeError("whisper package is required to load models") from e

    # Normalize device: if a cuda index was requested but doesn't exist,
    # remap to an available CUDA device or fall back to cpu.
    chosen = device
    if torch is not None and device and device.startswith("cuda"):
        try:
            # Accept forms: "cuda", "cuda:0", "cuda:1"
            if device == "cuda":
                # pick default cuda:0
                chosen = "cuda:0"
            elif device.startswith("cuda:"):
                idx_part = device.split(":", 1)[1]
                try:
                    idx = int(idx_part)
                except Exception:
                    idx = 0
                available = torch.cuda.device_count()
                if available == 0:
                    chosen = "cpu"
                elif idx >= available:
                    # remap to last available device
                    chosen = f"cuda:{max(0, available-1)}"
                else:
                    chosen = f"cuda:{idx}"
        except Exception:
            # In case of any inspection error, fall back to cpu
            chosen = "cpu"

    try:
        # whisper.load_model accepts a device string; it will internally call
        # torch.load with map_location where appropriate.
        model = whisper.load_model(model_dir, device=chosen)
        return model
    except RuntimeError as exc:
        # Common problem: checkpoint serialized to a CUDA index that doesn't
        # exist on this machine. Try to recover by mapping to cpu or cuda:0.
        msg = str(exc)
        if "torch.cuda.device_count() is" in msg or "deserializ" in msg:
            # Retry on CPU first
            try:
                model = whisper.load_model(model_dir, device="cpu")
                return model
            except Exception:
                # Final fallback: re-raise original
                raise
        raise


def _cli():
    parser = argparse.ArgumentParser(
        description="Whisper loader helper (device selection)"
    )
    parser.add_argument(
        "--model-dir",
        required=False,
        help=("Local model dir or name to load (dry-run shows device)"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually load model; just echo chosen device",
    )
    parser.add_argument(
        "--force-gpu",
        action="store_true",
        help=(
            "Temporarily force GPU for this run (overrides env) - "
            "convenience only"
        ),
    )
    parser.add_argument(
        "--cuda-device",
        help="CUDA device index or string (e.g. 0 or cuda:1)",
    )
    args = parser.parse_args()

    # allow CLI overrides to feed into decision function
    force_env = "1" if args.force_gpu else os.environ.get("WHISPER_FORCE_GPU")
    cuda_env = args.cuda_device or os.environ.get("WHISPER_CUDA_DEVICE")
    device = get_preferred_device(force_env, cuda_env)
    print(f"Selected device: {device}")

    if args.dry_run:
        print("Dry run: not importing or loading whisper model.")
        return

    # Attempt actual load (this can be slow/heavy)
    model_dir = args.model_dir or "small"
    print(
        f"Loading whisper model from: {model_dir} (this may take a while)"
    )
    model = load_whisper_model(model_dir, device=device, dry_run=False)
    print(f"Loaded model: {type(model)}")


if __name__ == "__main__":
    _cli()
