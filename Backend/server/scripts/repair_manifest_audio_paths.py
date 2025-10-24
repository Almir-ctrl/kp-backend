"""Repair manifest audio paths by matching manifest audio stems
to files in uploads/.

Usage:
    python server/scripts/repair_manifest_audio_paths.py \
            --manifest manifests/run1_small.jsonl
"""
from pathlib import Path
import json
import argparse

ROOT = Path(__file__).resolve().parents[2]
UPLOADS = ROOT / "uploads"


def build_lookup():
    # Prefer audio files when multiple files share the same stem.
    audio_exts = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    lookup = {}
    # First pass: audio files
    for p in UPLOADS.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() in audio_exts:
            lookup[p.stem.lower()] = str(p)
    # Second pass: other files (e.g., .txt) only if no audio found
    for p in UPLOADS.iterdir():
        if not p.is_file():
            continue
        stem = p.stem.lower()
        if stem not in lookup:
            lookup[stem] = str(p)
    return lookup


def repair(manifest: Path):
    if not manifest.exists():
        print("Manifest not found:", manifest)
        return
    lookup = build_lookup()
    out_lines = []
    changed = 0
    audio_exts = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    with manifest.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            audio = obj.get("audio")
            stem = Path(audio).stem.lower()
            replaced = False
            if stem in lookup:
                new_path = lookup[stem]
                if new_path != audio:
                    # If the current mapping is to a non-audio file, prefer
                    # to find an audio file via substring match.
                    if Path(new_path).suffix.lower() not in audio_exts:
                        # attempt substring audio search below
                        pass
                    else:
                        obj["audio"] = new_path
                        changed += 1
                        replaced = True

            if not replaced:
                # try substring match against filenames (case-insensitive)
                found = None
                target = stem
                for p in UPLOADS.iterdir():
                    if not p.is_file():
                        continue
                    name = p.name.lower()
                    if target in name:
                        # prefer audio extensions
                        if p.suffix.lower() in audio_exts:
                            found = str(p)
                            break
                        if not found:
                            found = str(p)
                if found:
                    obj["audio"] = found
                    changed += 1
            out_lines.append(json.dumps(obj, ensure_ascii=False))

    if changed > 0:
        backup = manifest.with_suffix(".bak.jsonl")
        manifest.replace(backup)
        manifest.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        print(f"Repaired {changed} entries. Original backed up to {backup}")
    else:
        print("No changes needed.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--manifest",
        default=str(ROOT / "manifests" / "run1_small.jsonl"),
    )
    args = p.parse_args()
    repair(Path(args.manifest))


if __name__ == "__main__":
    main()
