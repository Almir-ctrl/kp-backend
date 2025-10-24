"""Dataset inventory scanner.

Scans `uploads/` and writes `manifests/dataset_inventory.csv` with columns:
    filename,size_bytes,duration_seconds,transcript_present,
    transcript_path,sha256,language_guess,duplicate_of

Usage:
        python server/scripts/dataset_inventory.py

Tries to read audio duration via soundfile (pysoundfile) or wave. If neither
is available the duration field will be left blank.
"""
from __future__ import annotations
import csv
import hashlib
from pathlib import Path
from typing import Optional

try:
    import soundfile as sf
except Exception:
    sf = None

UPLOADS = Path(__file__).resolve().parents[2] / "uploads"
MANIFESTS = Path(__file__).resolve().parents[2] / "manifests"

MANIFESTS.mkdir(parents=True, exist_ok=True)


def sha256_of_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_duration_seconds(p: Path) -> Optional[float]:
    # Try soundfile
    try:
        if sf:
            info = sf.info(str(p))
            if info.frames and info.samplerate:
                return float(info.frames) / float(info.samplerate)
    except Exception:
        pass
    # Fallback for wav via wave
    try:
        import wave

        if p.suffix.lower() == ".wav":
            with wave.open(str(p), "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate()
                if frames and rate:
                    return float(frames) / float(rate)
    except Exception:
        pass
    return None


def guess_language_from_transcript(p: Path) -> Optional[str]:
    # Very small heuristic: check for presence of specific characters or common words
    try:
        text = p.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return None
    # simple keyword checks
    if any(w in text for w in ["hvala", "molim", "dobar", "dobro"]):
        return "bs/cs/hr-south"  # generic B/C/S
    if any(ch in text for ch in ["ђ", "ђ"]):
        return "sr-cyrillic"
    return None


def find_transcript_for_audio(p: Path) -> Optional[Path]:
    # look for same-name.txt or same-name.norm.txt or same-name.json
    base = p.with_suffix("")
    for ext in [".txt", ".norm.txt", ".trans.txt", ".json"]:
        candidate = base.with_suffix(ext)
        if candidate.exists():
            return candidate
    # also try sibling transcripts with same stem
    for other in p.parent.glob(base.name + "*"):
        if other.suffix.lower() in [".txt", ".json"] and other.exists():
            return other
    return None


def run():
    rows = []
    hash_map = {}
    if not UPLOADS.exists():
        print("No uploads/ directory found at", UPLOADS)
        return

    for p in UPLOADS.rglob("*"):
        if p.is_file():
            rel = p.relative_to(UPLOADS)
            size = p.stat().st_size
            sha = sha256_of_file(p)
            duration = get_duration_seconds(p)
            transcript = find_transcript_for_audio(p)
            transcript_present = bool(transcript)
            transcript_path = str(transcript) if transcript else ""
            lang = guess_language_from_transcript(transcript) if transcript else ""
            duplicate_of = ""
            if sha in hash_map:
                duplicate_of = hash_map[sha]
            else:
                hash_map[sha] = str(rel)

            rows.append({
                "filename": str(rel).replace("\\", "/"),
                "size_bytes": size,
                "duration_seconds": "{:.3f}".format(duration) if duration else "",
                "transcript_present": str(transcript_present),
                "transcript_path": transcript_path,
                "sha256": sha,
                "language_guess": lang or "",
                "duplicate_of": duplicate_of,
            })

    out_csv = MANIFESTS / "dataset_inventory.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "filename",
            "size_bytes",
            "duration_seconds",
            "transcript_present",
            "transcript_path",
            "sha256",
            "language_guess",
            "duplicate_of",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print("Wrote", out_csv)


if __name__ == "__main__":
    run()
