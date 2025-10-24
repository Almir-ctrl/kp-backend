"""Forced-alignment helper.

Attempts to use installed aligners (best-effort). If none are available,
falls back to a simple heuristic: split transcript into sentences and
distribute timestamps evenly across the audio duration.

Writes per-file outputs to: outputs/{id}/transcription_base.json and .txt
"""

from pathlib import Path
import json
import argparse
import re
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "outputs"
OUTROOT.mkdir(parents=True, exist_ok=True)


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def approx_align(transcript: str, duration: float) -> Dict:
    sentences = split_sentences(transcript)
    if not sentences:
        return {"text": transcript, "segments": []}

    total_words = sum(len(s.split()) for s in sentences)
    segs = []
    cursor = 0.0
    for s in sentences:
        words = s.split()
        wcount = len(words)
        if total_words > 0:
            seg_dur = duration * (wcount / total_words)
        else:
            seg_dur = duration / max(1, len(sentences))
        start = cursor
        end = min(duration, cursor + seg_dur)
        word_items = []
        if wcount > 0 and end > start:
            per = (end - start) / wcount
            for i, w in enumerate(words):
                wstart = round(start + i * per, 3)
                wend = round(start + (i + 1) * per, 3)
                word_items.append({"word": w, "start": wstart, "end": wend})

        segs.append(
            {
                "text": s,
                "start": round(start, 3),
                "end": round(end, 3),
                "words": word_items,
            }
        )
        cursor = end

    return {"text": transcript, "segments": segs}


def write_outputs(file_id: str, alignment: Dict):
    outdir = OUTROOT / file_id
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / "transcription_base.json"
    txt_path = outdir / "transcription_base.txt"
    json_path.write_text(
        json.dumps(alignment, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with txt_path.open("w", encoding="utf-8") as fh:
        fh.write(alignment.get("text", ""))
    print(f"Wrote alignment for {file_id} -> {json_path}")


def process_manifest(manifest: Path):
    if not manifest.exists():
        print("Manifest not found:", manifest)
        return 1
    with manifest.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            file_id = obj.get("id")
            transcript = (obj.get("transcript") or "").strip()
            duration = obj.get("duration")

            if not transcript:
                print(f"Skipping {file_id}: no transcript")
                continue

            # attempt to compute duration from processed audio if missing
            if duration is None:
                proc = ROOT / "data" / "processed" / f"{file_id}.wav"
                if proc.exists():
                    try:
                        import soundfile as sf

                        info = sf.info(str(proc))
                        duration = float(info.frames) / float(info.samplerate)
                    except Exception:
                        duration = None

            # Try an external aligner if installed (best-effort)
            used = False
            try:
                # prefer a direct import check to avoid importlib.util usage
                import importlib

                try:
                    mod = importlib.import_module("whisper_timestamped")
                except Exception:
                    mod = None

                if mod and hasattr(mod, "align"):
                    # many third-party aligners accept different args.
                    # Try alignment in a best-effort manner.
                    aln = mod.align(
                        transcript, file=str(Path(obj.get("audio")))
                    )
                    write_outputs(file_id, aln)
                    used = True
                if used:
                    continue
            except Exception:
                # ignore and fallback
                pass

            # fallback to approximate alignment
            if duration is None:
                print(f"No duration for {file_id}; cannot align. Skipping.")
                continue
            aln = approx_align(transcript, float(duration))
            write_outputs(file_id, aln)

    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    args = p.parse_args()
    return process_manifest(Path(args.manifest))


if __name__ == "__main__":
    raise SystemExit(main())
