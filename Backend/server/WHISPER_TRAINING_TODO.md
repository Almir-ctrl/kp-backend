# Whisper Training — Comprehensive TODO

This document exports the project's comprehensive training plan (dataset → train → evaluate → deploy). It was generated from the in-repo task list and is intended as the single-source TODO for the Whisper fine-tuning work.

Status legend
- NOT STARTED — work not yet begun
- IN PROGRESS — work started
- COMPLETED — done

---

## 1. Define training contract & success criteria
- Status: NOT STARTED
- Description: Write a short contract covering inputs (audio formats, transcripts), outputs (saved model, tokenizer, metrics), supported languages (Bosnian/Croatian/Serbian), evaluation metrics (WER/CER targets), compute constraints, and acceptance criteria.
- Files / location: `server/scripts/WHISPER_TRAINING_README.md` (update)
- Acceptance: Contract doc present and approved.

## 2. Inventory existing dataset
- Status: NOT STARTED
- Description: Scan `uploads/` and other local dirs and produce `manifests/dataset_inventory.csv` with columns: filename, size, duration (if available), transcript present, language guess, duplicate flag.
- Acceptance: inventory file created and reviewed.

## 3. Harvest more audio (YouTube + remote)
- Status: NOT STARTED
- Description: Implement `server/scripts/fetch_youtube_dataset.py` to call backend YouTube downloader endpoints and fetch Bosnian/Croatian/Serbian audio into `uploads/`.
- Acceptance: Script can download sample videos and update `manifests/dataset_inventory.csv`.

## 4. Deduplicate and validate files
- Status: NOT STARTED
- Description: `server/scripts/validate_and_dedupe.py`: compute file hashes, move duplicates to `uploads/duplicates/`, verify audio readability, and check transcript availability.
- Acceptance: validation report saved to `manifests/validation_report.json` and duplicates relocated.

## 5. Normalize and clean transcripts
- Status: NOT STARTED
- Description: `server/scripts/normalize_transcripts.py` to normalize punctuation, remove bracketed annotations, handle Cyrillic/Latin normalization, enforce UTF-8, and output `.norm.txt` files.
- Acceptance: cleaned transcripts produced for >=95% of files; summary report generated.

## 6. Prepare dataset manifest (small test + full)
- Status: NOT STARTED
- Description: Use `server/scripts/prepare_whisper_dataset.py` to produce JSONL manifests for training: `manifests/run1_small.jsonl` (small) and `manifests/run1.jsonl` (full).
- Acceptance: manifests exist and contain valid JSONL entries with `id`, `audio`, `transcript`, `duration`.

## 7. Audio preprocessing (resample/mono/normalize)
- Status: NOT STARTED
- Description: `server/scripts/preprocess_whisper_audio.py` to resample (target 16k or 16k/16-bit), convert to mono, trim silence, and optionally augment (noise, speed). Save to `data/processed/`.
- Acceptance: processed files exist and durations match manifest.

## 8. Forced-alignment (timestamps)
- Status: NOT STARTED
- Description: Add forced alignment using `aeneas`, `whisper-timestamped` or other aligner. Produce `outputs/{file_id}/transcription_base.json` and `.txt` with timestamps.
- Acceptance: timestamps produced for ≥80% dataset and format matches frontend needs.

## 9. Tokenizer & processor selection
- Status: NOT STARTED
- Description: Decide on tokenizer/processor (HF `WhisperProcessor` recommended). Implement `server/scripts/build_processor.py` to create and save processor via `save_pretrained()`.
- Acceptance: processor saved under `models/processor/` and tokenizes sample text.

## 10. Set up reproducible environment
- Status: NOT STARTED
- Description: Create `requirements-train.txt` or `pyproject.toml` with pinned deps (torch, torchaudio, transformers, datasets, accelerate, jiwer). Add `scripts/setup_env.ps1` for Windows setup.
- Acceptance: documented environment and a smoke command to check torch+CUDA.

## 11. Baseline training run (small) — mock
- Status: COMPLETED
- Description: Mock trainer implemented (`server/scripts/train_whisper.py`) and smoke test (`tests/test_train_smoke.py`). Confirms training loop and artifact writing.
- Acceptance: smoke test passes; baseline checkpoint exists.

## 12. Full Hugging Face training recipe
- Status: NOT STARTED
- Description: Implement `server/scripts/train_whisper_hf_full.py` using `datasets` and `WhisperForConditionalGeneration` (or compatible). Data collator, Trainer, checkpointing, logging, fp16 support.
- Acceptance: script can run on small subset and save via `save_pretrained()`.

## 13. Hyperparameter tuning & sweeps
- Status: NOT STARTED
- Description: Add hyperparameter sweeps using `optuna`/`ray`/HF sweeper. Track lr, batch size, weight decay, warmup, gradient accumulation.
- Acceptance: at least one sweep executed and results recorded.

## 14. Checkpointing, resume, and artifact storage
- Status: NOT STARTED
- Description: Ensure periodic checkpoints saved under `models/whisper/<run>/checkpoints/`. Add resume support and optional upload to S3/GCS.
- Acceptance: resume verified by restarting from a checkpoint.

## 15. Evaluation: WER/CER and per-language metrics
- Status: NOT STARTED
- Description: Implement `server/scripts/evaluate_model.py` using `jiwer` to compute WER/CER and per-language metrics.
- Acceptance: evaluation runs on validation set and writes `manifests/eval_<run>.json`.

## 16. Model export & packaging
- Status: NOT STARTED
- Description: `server/scripts/package_model.py` to export model with `save_pretrained()` and write run manifest and README.
- Acceptance: `models/whisper/<run>/` contains `config.json` and model weights (bin or safetensors) plus processor artifacts.

## 17. Integrate model with backend endpoints
- Status: NOT STARTED
- Description: Wire model into backend transcription endpoints (`app.py` / `server/*`). Add API to list trained models and transcribe using selected model.
- Acceptance: `/process/whisper/<file_id>` returns transcription JSON for sample input.

## 18. CI tests & smoke runs
- Status: NOT STARTED
- Description: Add GitHub Actions job `ci-train-smoke.yml` to run smoke tests on PRs. Keep tests fast and mock-based.
- Acceptance: CI job passes on PRs.

## 19. Data governance, licensing & privacy
- Status: NOT STARTED
- Description: Document dataset provenance in `DATA_LICENSES.md` and add removal steps for copyrighted data.
- Acceptance: `DATA_LICENSES.md` exists.

## 20. Security & secrets management
- Status: NOT STARTED
- Description: Ensure API keys/HF tokens stored in CI secrets; add `.gitignore` entries for `.env`.
- Acceptance: no secrets in repo and CI uses secrets.

## 21. PowerShell auto-allow helper
- Status: NOT STARTED
- Description: Add `scripts/enable-pwsh-allow.ps1` to set ExecutionPolicy CurrentUser Bypass and run `Unblock-File` for scripts. Add `.vscode/tasks.json` entry to run it and document security warnings.
- Acceptance: script and task present and documented.

## 22. Documentation & training guide
- Status: NOT STARTED
- Description: Expand `WHISPER_TRAINING_README.md` to include dataset prep, preprocessing, training commands, GPU tips, and troubleshooting (PowerShell commands included).
- Acceptance: README contains reproducible run and troubleshooting guide.

## 23. Monitoring, logging and request tracing
- Status: NOT STARTED
- Description: Add structured logging for training jobs, include `X-Request-ID`, GPU utilization, loss/step logging. Save logs to `logs/training/<run>.log`.
- Acceptance: logs include request-id and step-level metrics.

## 24. Post-training features (karaoke sync)
- Status: NOT STARTED
- Description: Use transcriptions + forced-alignment to create karaoke `.lrc` files and integrate with frontend lyric highlighting.
- Acceptance: frontend displays word-level highlighting for a sample run and `outputs/<file_id>/karaoke.lrc` exists.

## 25. Plan timeline & resource cost estimate
- Status: NOT STARTED
- Description: Produce `PLANNING.md` with timeline, estimated GPU-hours and storage needs based on dataset size and model choice.
- Acceptance: `PLANNING.md` created and approved.

## 26. Audit dataset balance and language coverage
- Status: NOT STARTED
- Description: Analyze dataset for class balance (speakers, dialects, noise levels) and language distribution (B/C/S). Generate a report `manifests/dataset_balance.json` with recommendations for rebalancing.
- Acceptance: balance report created with actionable recommendations.

## 27. Create train/validation/test splits
- Status: NOT STARTED
- Description: Implement `server/scripts/split_dataset.py` to generate reproducible splits (seeded) and store manifests for each split under `manifests/splits/`. Prefer speaker-disjoint splits.
- Acceptance: splits saved and reproducible using seed.

## 28. Data augmentation recipes
- Status: NOT STARTED
- Description: Add augmentation scripts (`scripts/augment_audio.py`) supporting noise injection, speed changes, pitch shift, and reverberation. Provide configuration for probabilistic augmentation during training.
- Acceptance: augmentation pipeline tested on small subset and config saved under `configs/augment.yaml`.

## 29. Create Docker training image
- Status: NOT STARTED
- Description: Add `Dockerfile.train` to install pinned training deps and `docker-compose.train.yml` for GPU-enabled training runs. Include entrypoint to run sample training job.
- Acceptance: image builds and small training job runs in container (mock path allowed).

## 30. Evaluation visualizations and dashboards
- Status: NOT STARTED
- Description: Add scripts to produce confusion matrices, error heatmaps, and a small HTML dashboard to explore WER/CER per-length/per-speaker/per-language.
- Acceptance: dashboard generated for one run and saved to `reports/<run>/index.html`.

---

Suggested immediate next actions
1. Update `server/scripts/WHISPER_TRAINING_README.md` with the training contract (task 1). I can draft it.
2. Run the dataset inventory (task 2). I can run a scanner and write `manifests/dataset_inventory.csv` using the current `uploads/` folder.
3. Normalize transcripts (task 5) to prepare `manifests/run1_small.jsonl` for a small HF test.

If you want me to start, say: "Start task 2" (inventory) or "Start task 1" (contract) and I'll proceed without asking further clarifying questions.

---

# Bigger plan (phased roadmap)

This section expands the TODO into a phased roadmap you can follow as a project plan. Each phase lists deliverables, rough time estimates, and dependencies.

Phase 0 — Project kickoff & training contract (1-2 days)
- Deliverable: training contract in `WHISPER_TRAINING_README.md` listing inputs, outputs, supported languages, WER/CER targets and acceptance criteria.

Phase 1 — Dataset inventory & harvesting (2-5 days)
- Deliverable: `manifests/dataset_inventory.csv` and initial harvested audio snippets.
- Dependencies: running backend downloader or manual URL list.

Phase 2 — Cleaning, validation & splits (3-7 days)
- Deliverable: validated dataset, cleaned transcripts, reproducible splits in `manifests/splits/`.
- Details: dedupe, transcript normalization, language tagging, speaker heuristics.

Phase 3 — Data processing & augmentation (3-6 days)
- Deliverable: processed audio under `data/processed/`, augmentation configs in `configs/augment.yaml`.

Phase 4 — Small-scale HF experiments (4-8 days)
- Deliverable: `train_whisper_hf_full.py`, small HF run on `run1_small.jsonl`, baseline model saved under `models/whisper/<run>`.

Phase 5 — Scaling, tuning & CI (4-10 days)
- Deliverable: hyperparameter sweeps, checkpointing, resume logic, CI smoke runs, and Docker training image.

Phase 6 — Evaluation & integration (3-6 days)
- Deliverable: evaluation reports, dashboards, backend integration endpoint for transcription and karaoke sync.

Phase 7 — Release & governance (2-4 days)
- Deliverable: packaged artifacts, `DATA_LICENSES.md`, `PLANNING.md`, and model registry entry.

Ongoing — Continuous improvement
- Active learning loop, scheduled retraining, dataset expansion, monitoring and cost optimization.

If you'd like, I can now:
- Draft the Training Contract (Phase 0).
- Start the dataset inventory and produce `manifests/dataset_inventory.csv` (Phase 1).
- Start implementing transcript normalization (Phase 2).

Say which one to start or let me pick the most useful next step (I recommend dataset inventory). 

