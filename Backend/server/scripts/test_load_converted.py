import sys
from pathlib import Path
import traceback


def main():
    p = (
        Path(__file__).resolve().parents[2]
        / 'models'
        / 'whisper'
        / 'openai_whisper-large-v2'
        / 'model_converted.pt'
    )
    print('Trying to load converted checkpoint:', p)
    try:
        import whisper
        m = whisper.load_model(str(p), device='cpu')
        print('Loaded model:', type(m))
        return 0
    except Exception:
        print('Failed to load converted checkpoint:')
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
