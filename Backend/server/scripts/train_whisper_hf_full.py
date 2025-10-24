"""Full HF training recipe scaffold for Whisper fine-tuning.

This implements a minimal, runnable Hugging Face Trainer flow that can be
used for small smoke runs. It expects a JSONL manifest with fields:
  id, audio, transcript, duration

Usage examples:
  python train_whisper_hf_full.py --manifest manifests/run1_small.jsonl --output models/whisper/run1 --max-steps 100

Notes:
- If `--dry-run` is provided the script validates the manifest and writes
  metadata without starting training.
"""

from pathlib import Path
import argparse
import json
from typing import Dict, Any


def write_metadata(outdir: Path, manifest: str, samples: int, note: str = ""):
    outdir.mkdir(parents=True, exist_ok=True)
    meta = {"manifest": manifest, "samples": samples, "notes": note}
    (outdir / "metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print("Wrote run metadata to", outdir / "metadata.json")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--manifest",
        required=True,
        help=(
            "JSONL manifest with id,audio,transcript,duration"
        ),
    )
    p.add_argument(
        "--output",
        default="models/whisper/run1",
        help="Output model directory",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=1000,
        help="Max training steps (small)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifest and exit (no training)",
    )
    p.add_argument(
        "--model",
        default="openai/whisper-small",
        help="Base HF model to fine-tune",
    )
    return p.parse_args()


def quick_manifest_count(path: Path) -> int:
    if not path.exists():
        return 0
    c = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                c += 1
    return c


def load_manifest_as_dataset(manifest_path: str):
    # returns a HF Dataset object built from the JSONL manifest
    from datasets import load_dataset

    ds = load_dataset("json", data_files=manifest_path, split="train")
    return ds


def prepare_data_collator_and_processor(output_dir: Path, model_id: str):
    from transformers import WhisperProcessor

    proc_dir = output_dir / "processor"
    # prefer local processor if present
    if proc_dir.exists():
        print("Loading local processor from:", proc_dir)
        processor = WhisperProcessor.from_pretrained(str(proc_dir))
    else:
        print("Downloading processor from model id:", model_id)
        processor = WhisperProcessor.from_pretrained(model_id)
        processor.save_pretrained(str(proc_dir))

    # data collator for seq2seq
    from dataclasses import dataclass

    @dataclass
    class DataCollatorSpeechSeq2Seq:
        processor: WhisperProcessor

        def __call__(self, features: list) -> Dict[str, Any]:
            # features: list of dicts with 'input_values' and 'labels' already
            input_features = [f["input_features"] for f in features]
            label_features = [f["labels"] for f in features]
            batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
            batch_labels = self.processor.tokenizer.pad(label_features, return_tensors="pt")
            batch["labels"] = batch_labels["input_ids"]
            return batch

    collator = DataCollatorSpeechSeq2Seq(processor)
    return processor, collator


def main():
    args = parse_args()
    outdir = Path(args.output)

    # quick manifest validation / dry-run
    count = quick_manifest_count(Path(args.manifest))
    if count == 0:
        print("Manifest not found or empty:", args.manifest)
        return 2

    # If user asked for dry-run just write metadata and exit
    if args.dry_run:
        write_metadata(outdir, args.manifest, count, note="dry-run: manifest validated")
        return 0

    # attempt to import HF libs and perform a minimal training run
    try:
        import torch
        from transformers import (
            WhisperForConditionalGeneration,
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments,
        )
        # datasets and jiwer may be used later; they are imported lazily elsewhere
    except Exception as exc:
        print(
            "Missing HF training dependencies or optional libs. "
            "Install and re-run:"
        )
        print(
            "  pip install 'transformers[torch]' datasets accelerate jiwer"
            " sentencepiece safetensors"
        )
        write_metadata(outdir, args.manifest, count, note="dry-run: missing libs")
        print("Error:", exc)
        return 3

    # load dataset
    print("Loading manifest as dataset:", args.manifest)
    ds = load_manifest_as_dataset(args.manifest)

    # minimal preprocessing: map audio -> input_features and labels

    # prepare processor (saves into outdir/processor)
    processor, collator = prepare_data_collator_and_processor(outdir, args.model)

    # small map fn to compute input features and tokenized labels
    def prepare_example(batch):
        # batch['audio'] should be path to file
        audio_path = batch.get("audio")
        # feature extractor accepts numpy array, but for small runs we use
        # the processor
        try:
            import soundfile as sf

            speech_array, sr = sf.read(str(audio_path))
        except Exception:
            # fallback: empty array
            speech_array = [0.0]
            sr = 16000

        # feature_extractor/tokenizer are dynamic attrs on WhisperProcessor
        input_features = (
            processor.feature_extractor(
                speech_array, sampling_rate=sr
            ).input_features[0]  # type: ignore[attr-defined]
        )
        labels = (
            processor.tokenizer(
                batch.get("transcript", ""), add_special_tokens=True
            ).input_ids  # type: ignore[attr-defined]
        )
        return {"input_features": input_features, "labels": labels}

    print("Preparing dataset (this may take a bit)...")
    # ds.column_names can be a list or mapping; normalize to list[str]
    colnames = getattr(ds, "column_names", None)
    if isinstance(colnames, (list, tuple)):
        remove_cols = list(colnames)
    else:
        try:
            remove_cols = list(colnames.keys()) if colnames is not None else []
        except Exception:
            remove_cols = []

    ds_prepared = ds.map(prepare_example, remove_columns=remove_cols)

    # training args
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(outdir),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=1,
        fp16=torch.cuda.is_available(),
        num_train_epochs=1,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        max_steps=args.max_steps,
        predict_with_generate=True,
    )

    # model
    print("Loading model:", args.model)
    model = WhisperForConditionalGeneration.from_pretrained(args.model)

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=ds_prepared,
        data_collator=collator,
    )

    print("Starting training (small smoke run)...")
    trainer.train()

    print("Training finished. Saving model to", outdir)
    model.save_pretrained(str(outdir))
    processor.save_pretrained(str(outdir / "processor"))
    write_metadata(
        outdir,
        args.manifest,
        count,
        note="trained: see model files",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
