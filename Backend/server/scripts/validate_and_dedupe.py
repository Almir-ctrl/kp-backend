#!/usr/bin/env python3
"""Validate inventory and move duplicates to uploads/duplicates.

Reads `manifests/dataset_inventory.csv`, moves duplicate files to
`uploads/duplicates/`, checks basic audio readability, and writes a
validation report to `manifests/validation_report.json`.

Usage:
    python server/scripts/validate_and_dedupe.py
"""
import csv
import json
import shutil
from pathlib import Path
from typing import List, Dict

try:
    import soundfile as sf  # optional, used for a stronger readability check
except Exception:
    sf = None

ROOT = Path(__file__).resolve().parents[2]
UPLOADS = ROOT / "uploads"
MANIFESTS = ROOT / "manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)
DUPE_DIR = UPLOADS / "duplicates"
DUPE_DIR.mkdir(parents=True, exist_ok=True)


def check_audio_readable(p: Path) -> bool:
    # Prefer using soundfile if available
    try:
        if sf:
            with sf.SoundFile(str(p)) as f:
                _ = f.frames
            return True
    except Exception:
        pass
    # Fallback heuristics: extension + file size
    if p.suffix.lower() in [".wav", ".mp3", ".flac"] and p.exists():
        try:
            return p.stat().st_size > 1024
        except Exception:
            return False
    return False


def run():
    inventory = MANIFESTS / "dataset_inventory.csv"
    if not inventory.exists():
        print("Inventory not found:", inventory)
        return

    moved: List[Dict] = []
    unreadable: List[Dict] = []
    missing: List[Dict] = []

    with inventory.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            filename = row.get("filename")
            if not filename:
                missing.append({"filename": filename})
                continue

            file_path = ROOT / row.get("path", filename)
            if not file_path.exists():
                missing.append({"filename": filename})
                continue

            # Move duplicates if flagged
            dup_flag = row.get("duplicate", "").strip().lower()
            if dup_flag in ("true", "1"):
                target = DUPE_DIR / file_path.name
                try:
                    shutil.move(str(file_path), str(target))
                    moved.append({"from": str(file_path), "to": str(target)})
                except Exception as e:
                    moved.append({"from": str(file_path), "error": str(e)})
                continue

            # Validate readable
            ok = check_audio_readable(file_path)
            if not ok:
                unreadable.append(
                    {"filename": filename, "path": str(file_path)}
                )

    # compute totals
    total_checked = 0
    with inventory.open("r", encoding="utf-8") as fh:
        total_checked = sum(1 for _ in fh) - 1

    report = {
        "total_files_checked": total_checked,
        "moved_duplicates": moved,
        "missing_files": missing,
        "unreadable_files": unreadable,
    }

    out = MANIFESTS / "validation_report.json"
    with out.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print("Validation complete. Report:", out)


if __name__ == "__main__":
    run()
