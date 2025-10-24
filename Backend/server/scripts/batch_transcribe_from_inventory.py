#!/usr/bin/env python3
"""Batch transcribe audio files using the backend Whisper endpoints.

Flow:
- Read `manifests/dataset_inventory.csv`.
- For each audio without a transcript_path, upload it to `/upload/whisper` to get
  a `file_id`, then POST `/process/whisper/{file_id}` to request transcription.

The script supports --dry-run to only show planned actions without network calls.
"""
from __future__ import annotations

import argparse
import csv
import json
# sys not needed
from pathlib import Path
from typing import List

try:
    import requests
except Exception:
    requests = None

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "manifests"
UPLOADS = ROOT / "uploads"
DEFAULT_BACKEND = "http://127.0.0.1:5000"


def read_inventory() -> List[dict]:
    csv_path = MANIFESTS / "dataset_inventory.csv"
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    rows = []
    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows


def upload_file(path: Path, backend: str) -> dict:
    if requests is None:
        raise RuntimeError("requests not available")
    url = backend.rstrip("/") + "/upload/whisper"
    with path.open("rb") as fh:
        files = {"file": (path.name, fh)}
        resp = requests.post(url, files=files, timeout=300)
        return resp.json()


def process_file(
    file_id: str, backend: str, model_variant: str | None = None
) -> dict:
    if requests is None:
        raise RuntimeError("requests not available")
    url = backend.rstrip("/") + f"/process/whisper/{file_id}"
    payload = {}
    if model_variant:
        payload["model_variant"] = model_variant
    resp = requests.post(url, json=payload, timeout=600)
    try:
        return resp.json()
    except Exception:
        return {"http_status": resp.status_code, "text": resp.text}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model-variant", default=None)
    args = parser.parse_args(argv)

    rows = read_inventory()
    plan = []
    for r in rows:
        if r.get("transcript_path"):
            continue
        pth_rel = r.get("path")
        if not pth_rel:
            continue
        path = ROOT / pth_rel
        if not path.exists():
            continue
        plan.append(str(path))

    print(f"Found {len(plan)} files to transcribe. dry-run={args.dry_run}")

    results = []
    for p in plan:
        pth = Path(p)
        print("->", pth)
        if args.dry_run:
            results.append({"path": str(pth), "action": "dry-run"})
            continue

        try:
            up = upload_file(pth, args.backend)
        except Exception as e:
            results.append({"path": str(pth), "error": f"upload failed: {e}"})
            continue

        file_id = up.get("file_id") or up.get("id")
        if not file_id:
            results.append({"path": str(pth), "upload_response": up})
            continue

        try:
            proc = process_file(
                file_id, args.backend, args.model_variant
            )
        except Exception as e:
            results.append({
                "path": str(pth),
                "file_id": file_id,
                "error": str(e),
            })
            continue

        results.append({"path": str(pth), "file_id": file_id, "process": proc})

    out = MANIFESTS / "batch_transcribe_summary.json"
    out.write_text(
        json.dumps({"results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Wrote summary:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
