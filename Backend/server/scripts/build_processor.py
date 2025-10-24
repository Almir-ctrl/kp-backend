"""Build and save a WhisperProcessor or a compatible tokenizer/processor.

Creates `models/processor/` when transformers are installed. Otherwise it
creates a small placeholder and prints install instructions.
"""

from pathlib import Path
import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--model",
        default="openai/whisper-small",
        help="HF model id to base the processor on",
    )
    p.add_argument("--out", default="models/processor", help="Output dir")
    args = p.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        from transformers import WhisperProcessor
    except Exception:
        msg = (
            "transformers not installed. To build a real processor:"
            "\n  pip install transformers[torch] datasets"
        )
        print(msg)
        (outdir / "README.txt").write_text(
            "Placeholder processor. Install transformers and re-run\n"
            "to build a processor."
        )
        print("Wrote placeholder to", outdir)
        return 0

    print("Loading processor from:", args.model)
    proc = WhisperProcessor.from_pretrained(args.model)
    proc.save_pretrained(str(outdir))
    print("Saved processor to", outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
