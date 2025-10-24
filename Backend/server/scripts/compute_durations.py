"""Compute durations for audio files listed in a JSONL manifest.

Usage:
    python server/scripts/compute_durations.py \
            --manifest manifests/run1_processed.jsonl

Options:
        --replace-processed  Replace audio paths with processed WAVs when
                                                 a matching processed file exists.
    --write              Overwrite the manifest with updated duration
                                             fields (backups created).
"""
from pathlib import Path
import json
import argparse

try:
    import soundfile as sf
except Exception:
    sf = None

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def get_duration(path: Path):
    if not path.exists():
        return None
    if not sf:
        return None
    try:
        info = sf.info(str(path))
        return float(info.frames) / float(info.samplerate)
    except Exception:
        return None


def process_manifest(manifest: Path, replace_processed=False, write=False):
    if not manifest.exists():
        print("Manifest not found:", manifest)
        return 1
    out_lines = []
    changed = 0
    with manifest.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            audio = Path(obj.get("audio") or "")
            id_ = obj.get("id")

            # Optionally replace with processed file if available
            if replace_processed and id_:
                proc = PROCESSED / f"{id_}.wav"
                if proc.exists():
                    if str(proc) != str(audio):
                        obj["audio"] = str(proc)
                        changed += 1
                    audio = proc

            duration = get_duration(audio)
            if duration is not None:
                # round to 3 decimals
                dur = round(duration, 3)
                if obj.get("duration") != dur:
                    obj["duration"] = dur
                    changed += 1

            out_lines.append(json.dumps(obj, ensure_ascii=False))

    if write and changed > 0:
        backup = manifest.with_suffix(".bak.jsonl")
        manifest.replace(backup)
        manifest.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        print(
            f"Wrote updated manifest (backup at {backup}). "
            f"Changes: {changed}"
        )
    else:
        print(f"Dry run complete. Detected changes: {changed}")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--replace-processed", action="store_true")
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    manifest = Path(args.manifest)
    return process_manifest(
        manifest,
        replace_processed=args.replace_processed,
        write=args.write,
    )


if __name__ == "__main__":
    raise SystemExit(main())
