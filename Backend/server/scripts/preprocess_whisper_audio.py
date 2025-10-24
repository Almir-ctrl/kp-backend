"""Preprocess audio for Whisper training.

Reads a manifest (JSONL) or scans uploads/, resamples audio to 16 kHz mono,
and writes output WAV files to data/processed/<id>.wav. Uses soundfile +
resampy or librosa when available; otherwise copies the original file.

Usage:
  python server/scripts/preprocess_whisper_audio.py --manifest manifests/run1_small.jsonl
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
# typing imports removed (unused)

try:
    import soundfile as sf
except Exception:
    sf = None

try:
    import resampy
except Exception:
    resampy = None

try:
    import librosa
except Exception:
    librosa = None

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


def resample_and_save(src: Path, dst: Path, target_sr: int = 16000) -> bool:
    try:
        if not sf:
            # can't read; fallback to copy
            shutil.copy2(src, dst)
            return False
        data, sr = sf.read(str(src), always_2d=False)
        # make mono
        import numpy as np

        if data.ndim > 1:
            data = np.mean(data, axis=1)

        if sr != target_sr:
            if resampy:
                data = resampy.resample(data, sr, target_sr)
                sr = target_sr
            elif librosa:
                data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
                sr = target_sr
            else:
                # no resampler available: copy instead
                shutil.copy2(src, dst)
                return False

        # write as 16-bit PCM WAV
        sf.write(str(dst), data, samplerate=sr, subtype='PCM_16')
        return True
    except Exception:
        try:
            shutil.copy2(src, dst)
        except Exception:
            return False
        return False


def process_manifest(manifest: Path, target_sr: int = 16000):
    processed = []
    if not manifest.exists():
        print("Manifest not found:", manifest)
        return processed
    with manifest.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            audio = Path(obj.get("audio"))
            id_ = obj.get("id") or audio.stem
            outp = PROCESSED / f"{id_}.wav"
            if audio.exists():
                ok = resample_and_save(audio, outp, target_sr=target_sr)
                processed.append(
                    {
                        "id": id_,
                        "source": str(audio),
                        "out": str(outp),
                        "resampled": ok,
                    }
                )
            else:
                processed.append(
                    {
                        "id": id_,
                        "source": str(audio),
                        "out": str(outp),
                        "resampled": False,
                        "missing": True,
                    }
                )
    return processed


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--manifest",
        default=str(ROOT / "manifests" / "run1_small.jsonl"),
    )
    p.add_argument("--sr", type=int, default=16000)
    args = p.parse_args()
    manifest = Path(args.manifest)
    results = process_manifest(manifest, target_sr=args.sr)
    out = PROCESSED / "preprocess_report.json"
    out.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Preprocessing complete. Report:", out)


if __name__ == "__main__":
    main()
