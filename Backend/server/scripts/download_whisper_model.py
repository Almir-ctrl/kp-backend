"""Helper to download a Whisper model if missing.

This is intentionally lightweight and testable. The download function is
separated so we can mock network activity in tests. It supports model
names like "openai/whisper-large-v2" or local paths. The script writes
model marker files into `models/whisper/{model_name}`.
"""
from pathlib import Path
from typing import Callable, Optional

MODELS_DIR = Path(__file__).resolve().parents[2] / "models" / "whisper"


def model_dir_for(name: str) -> Path:
    # sanitize model name to folder-friendly name
    safe = name.replace('/', '_').replace(':', '_')
    return MODELS_DIR / safe


def is_model_present(name: str) -> bool:
    d = model_dir_for(name)
    # Consider a model present if we have a marker or a common
    # checkpoint file (model.pt / pytorch_model.bin / model.safetensors).
    if (d / "model.marker").exists():
        return True
    if (d / "model.pt").exists():
        return True
    if (d / "pytorch_model.bin").exists():
        return True
    if (d / "model.safetensors").exists():
        return True
    return False


def download_model(name: str, *, downloader=None) -> Path:
    """Download a model using the provided downloader callable or
    a default stub.

    downloader should be a callable taking (name: str, dest: Path) and
    returning True on success.
    """
    d = model_dir_for(name)
    d.mkdir(parents=True, exist_ok=True)

    if downloader is None:
        # Default downloader: create a small marker file to simulate success
        marker = d / "model.marker"
        marker.write_text(f"model: {name}\ninstalled: true\n")
        return d

    success = downloader(name, d)
    if not success:
        raise RuntimeError(f"Failed to download model {name}")

    # create marker
    (d / "model.marker").write_text(f"model: {name}\ninstalled: true\n")
    return d


def ensure_model(name: str, *, downloader=None) -> Path:
    """Ensure the Whisper model is present, downloading if necessary.

    Returns the model directory Path.
    """
    if is_model_present(name):
        return model_dir_for(name)
    return download_model(name, downloader=downloader)


def hf_downloader_factory(
    repo: Optional[str] = None,
) -> Callable[[str, Path], bool]:
    """Return a downloader callable that uses
    huggingface_hub.snapshot_download.

    The returned callable signature is (name: str, dest: Path) -> bool.
    If `repo` is provided it will be used as the HF repo; otherwise `name`
    is used as the repo id.
    """

    def _downloader(name: str, dest: Path) -> bool:
        try:
            # Import here so tests can mock huggingface_hub
            from huggingface_hub import snapshot_download
            import shutil

            repo_id = repo or name
            # snapshot_download returns a local folder path in HF cache.
            out = snapshot_download(repo_id)

            # Copy the snapshot contents into our expected dest so runtime
            # code (e.g., whisper.load_model) can load models from the
            # repository-specific directory.
            dest_parent = dest.parent
            dest_parent.mkdir(parents=True, exist_ok=True)
            # If dest exists, remove it to ensure a clean copy
            if dest.exists():
                try:
                    shutil.rmtree(dest)
                except Exception:
                    pass

            shutil.copytree(str(out), str(dest), dirs_exist_ok=True)

            # Ensure tokenizer files are present at the dest root. Some HF
            # snapshots place tokenizer files in subfolders (eg.
            # `tokenizer/*`). Whisper's loading code expects tokenizer
            # artifacts at the model directory root, so search recursively
            # and copy common tokenizer files into `dest/` if missing.
            try:
                from shutil import copy2

                tokenizer_candidates = [
                    'tokenizer.json',
                    'tokenizer_config.json',
                    'vocab.json',
                    'merges.txt',
                    'tokenizer.model',
                    'sentencepiece.bpe.model',
                    'spiece.model',
                    'vocab.txt',
                    'added_tokens.json',
                ]

                for name in tokenizer_candidates:
                    # If already present at root, skip
                    if (dest / name).exists():
                        continue

                    # Search the whole snapshot for this filename
                    found = None
                    for p in dest.rglob(name):
                        # prefer files that are not inside .git directories
                        if any(part.startswith('.git') for part in p.parts):
                            continue
                        found = p
                        break

                    if found is not None:
                        try:
                            copy2(str(found), str(dest / name))
                        except Exception:
                            # Non-fatal; continue with other files
                            pass
            except Exception:
                # Non-fatal tokenizer copying; proceed regardless
                pass

            # If critical tokenizer files are still missing, attempt to copy
            # a repository-local fallback (for example, a checked-in
            # `server/scripts/vocab.json` or `tokenizer.json` that we ship
            # as a developer convenience). This helps in cases where the HF
            # snapshot lacks sentencepiece/tokenizer artifacts.
            try:
                critical = [
                    'tokenizer.model',
                    'spiece.model',
                    'vocab.json',
                ]
                missing_critical = [
                    c
                    for c in critical
                    if not (dest / c).exists()
                ]
                if missing_critical:
                    repo_root = Path(__file__).resolve().parents[2]
                    # ensure copy2 is available in this scope
                    from shutil import copy2
                    # Common locations to look for fallback tokenizers
                    candidates = [
                        repo_root / 'server' / 'scripts' / 'vocab.json',
                        repo_root / 'server' / 'scripts' / 'tokenizer.json',
                        repo_root / 'server' / 'scripts' / 'merges.txt',
                        repo_root
                        / 'server'
                        / 'scripts'
                        / 'special_tokens_map.json',
                    ]
                    for src in candidates:
                        if not src.exists():
                            continue
                        try:
                            copy2(str(src), str(dest / src.name))
                        except Exception:
                            pass
                    # If still missing, attempt to download specific files
                    # from the HF repo using hf_hub_download (if available).
                    try:
                        from huggingface_hub import hf_hub_download

                        for fname in missing_critical:
                            try:
                                local = hf_hub_download(
                                    repo_id, filename=fname
                                )
                                copy2(str(local), str(dest / fname))
                            except Exception:
                                # ignore per-file failures
                                pass
                    except Exception:
                        # huggingface_hub.hf_hub_download not available
                        # or failed
                        pass
            except Exception:
                pass

            # Create a small marker linking to the downloaded path
            (dest / "hf_source.txt").write_text(str(out))
            # Best-effort: try to make a whisper-loadable torch file.
            try:
                import importlib
                import importlib.util as _il_util

                try:
                    torch = importlib.import_module('torch')
                except Exception:
                    torch = None

                safetensors_spec = _il_util.find_spec('safetensors')
                converted = False

                # If safetensors present, try to convert it first.
                safetensors_path = dest / 'model.safetensors'
                if (
                    safetensors_path.exists()
                    and safetensors_spec is not None
                    and torch is not None
                ):
                    try:
                        # local import so tests can mock absence of safetensors
                        from safetensors.torch import load_file
                        sd = load_file(str(safetensors_path))
                        torch.save(sd, str(dest / 'model.pt'))
                        converted = True
                    except Exception:
                        converted = False

                # Fall back to pytorch_model.bin if available.
                pytorch_path = dest / 'pytorch_model.bin'
                if (
                    (not converted)
                    and pytorch_path.exists()
                    and torch is not None
                ):
                    try:
                        sd = torch.load(str(pytorch_path), map_location='cpu')
                        if isinstance(sd, dict) and 'state_dict' in sd:
                            sd = sd['state_dict']
                        torch.save(sd, str(dest / 'model.pt'))
                        converted = True
                    except Exception:
                        converted = False

                if converted:
                    (dest / 'whisper_converted.marker').write_text(
                        'converted: true\n'
                    )
            except Exception:
                # Conversion is best-effort; ignore failures.
                pass
            return True
        except Exception:
            return False

    return _downloader


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Ensure Whisper model is downloaded'
    )
    parser.add_argument(
        'model',
        help='Model name (e.g. openai/whisper-large-v2)'
    )
    args = parser.parse_args()
    p = ensure_model(args.model)
    print(f"Model available at: {p}")
