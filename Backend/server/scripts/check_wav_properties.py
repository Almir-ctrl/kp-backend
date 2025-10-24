"""Quick check script to verify sample rate and channels of processed WAVs.

Usage:
  python server/scripts/check_wav_properties.py manifests/run1_processed.jsonl
"""
from pathlib import Path
import sys
import json

try:
    import soundfile as sf
except Exception:
    sf = None


def check(manifest_path: Path):
    if not manifest_path.exists():
        print('Manifest not found:', manifest_path)
        return 2
    with manifest_path.open('r', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            audio = Path(obj.get('audio'))
            if not audio.exists():
                print(f"MISSING: {audio}")
                continue
            if not sf:
                print(f"soundfile not installed — cannot inspect {audio}")
                continue
            try:
                info = sf.info(str(audio))
                print(
                    f"{audio.name}: samplerate={info.samplerate}, "
                    f"channels={info.channels}, subtype={info.subtype}"
                )
            except Exception as e:
                print(f"FAILED to read {audio}: {e}")
    return 0


if __name__ == '__main__':
    m = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path('manifests/run1_processed.jsonl')
    )
    sys.exit(check(m))
