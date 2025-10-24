#!/usr/bin/env python3
"""Fetch YouTube dataset helper

This script sends YouTube URLs to the local backend downloader endpoint and
optionally updates the local inventory by invoking the existing
`generate_dataset_inventory.py` script.

Usage examples:
  # dry-run (no network calls)
  python server/scripts/fetch_youtube_dataset.py --dry-run --urls urls.txt

  # run and then refresh inventory
  python server/scripts/fetch_youtube_dataset.py --urls urls.txt --update-inventory

The script expects the backend to expose an endpoint at
http://127.0.0.1:5000/download-youtube which accepts POST JSON {"url": "..."}
and returns a JSON object containing at least one of: file_id, file_path,
or success:true. The downloader in the backend typically saves downloads to
`uploads/` already; this script tolerates either behavior.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List

try:
    import requests
except Exception:  # pragma: no cover - best-effort import
    requests = None


DEFAULT_BACKEND = "http://127.0.0.1:5000"
DOWNLOAD_ENDPOINT = "/download-youtube"


def read_urls_from_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as f:
        urls = [line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")]
    return urls


def call_backend_download(url: str, backend: str) -> dict:
    if requests is None:
        raise RuntimeError(
            "requests package not available in this Python environment"
        )
    endpoint = backend.rstrip("/") + DOWNLOAD_ENDPOINT
    resp = requests.post(endpoint, json={"url": url}, timeout=300)
    try:
        return resp.json()
    except Exception:
        return {"http_status": resp.status_code, "text": resp.text}


def refresh_inventory(repo_root: Path) -> None:
    script = repo_root / "server" / "scripts" / "generate_dataset_inventory.py"
    if not script.exists():
        print("Inventory script not found; skipping inventory refresh.")
        return
    print(f"Refreshing inventory by running: {script}")
    subprocess.check_call([sys.executable, str(script)])


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--urls",
        help="Path to file with YouTube URLs (one per line)",
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help="Backend base URL",
    )
    parser.add_argument(
        "--update-inventory",
        action="store_true",
        help="Run inventory refresh after downloads",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call the backend; just show planned actions",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use embedded sample URLs for quick tests",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]

    urls: List[str] = []
    if args.sample:
        # Empty sample list - intentionally left blank so the user can edit.
        urls = [
            # Add sample B/C/S YouTube URLs here if you have them.
            # "https://www.youtube.com/watch?v=...",
        ]
    elif args.urls:
        urls = read_urls_from_file(Path(args.urls))
    else:
        print("No URLs provided. Use --urls or --sample to run a test.")
        return 2

    if not urls:
        print("URL list is empty. Nothing to do.")
        return 0

    print(f"Found {len(urls)} URLs. Dry-run={args.dry_run}")

    results = []
    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] Processing: {url}")
        if args.dry_run:
            print(
                "  Dry-run: would POST to "
                + args.backend.rstrip("/")
                + DOWNLOAD_ENDPOINT
            )
            results.append({"url": url, "action": "dry-run"})
            continue

        try:
            resp = call_backend_download(url, args.backend)
        except Exception as e:  # pragma: no cover - runtime behavior
            print(f"  Error calling backend for {url}: {e}")
            results.append({"url": url, "error": str(e)})
            continue

        # Best-effort interpretation of backend reply
        out = {"url": url, "response": resp}
        if isinstance(resp, dict):
            if resp.get("file_path"):
                out["file_path"] = resp.get("file_path")
            if resp.get("file_id"):
                out["file_id"] = resp.get("file_id")
            if resp.get("success") is True:
                out["downloaded"] = True
        results.append(out)

    # Write a summary JSON next to manifests folder
    manifests = repo_root / "manifests"
    manifests.mkdir(exist_ok=True)
    summary_path = manifests / "youtube_fetch_summary.json"
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump({"results": results}, fh, ensure_ascii=False, indent=2)

    print(f"Wrote summary: {summary_path}")

    if args.update_inventory and not args.dry_run:
        try:
            refresh_inventory(repo_root)
        except subprocess.CalledProcessError as e:
            print(f"Inventory refresh failed: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
