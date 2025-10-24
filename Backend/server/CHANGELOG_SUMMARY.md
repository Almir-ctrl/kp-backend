# Change Log & Session Summary

This summary documents recent code changes, scripts added/modified, runtime actions taken, verification results, and recommended next steps made during the current session (2025-10-22).

## High level goals

- Enable reliable GPU-backed Whisper inference using a converted Hugging Face Transformers checkpoint.
- Add robust loading logic (device selection / CUDA remapping) and fix encoding issues when writing output files.
- Provide a Transformers-based transcription fallback and deterministic comparison scripts.
- Improve frontend modal (ModelSelectorModal) integration and keep it synced with backend `/models` endpoint.

## Files added or modified

- server/scripts/whisper_loader.py (existing) — utility used to decide and normalize device strings (WHISPER_FORCE_GPU, WHISPER_CUDA_DEVICE). No change required; used by other scripts.
- server/scripts/transcribe_uploads.py (modified)
  - Fixed Unicode write errors by writing all output files with UTF-8 encoding.
  - Now uses `whisper_loader.load_whisper_model` (if present) to handle robust device selection and remapping when loading a converted checkpoint.
  - Writes the following outputs under `outputs/<slug>/`:
    - `transcription_base.txt` (UTF-8)
    - `transcription_base.json` (UTF-8, ensure_ascii=False)
    - `karaoke.lrc` (UTF-8)
    - `metadata.json` (UTF-8)

- server/scripts/convert_transformers_to_whisper.py (existing)
  - Converter iteratively improved in earlier work (not modified in this session) with many heuristic passes to map Transformers checkpoint keys into a Whisper-compatible checkpoint. Mapping report and `model_converted.pt` are produced in `models/whisper/...`.

- server/scripts/compare_transformers_vs_whisper.py (existing)
  - Deterministic comparison script to transcribe a deterministic TTS sample and report WER / token overlap between Transformers runtime and the converted Whisper checkpoint. Used previously to debug fidelity.

- components/windows/ModelSelectorModal.tsx (frontend) — inspected
  - Modal shows available models and variations (Whisper, Gemma 3N) and allows selection.
  - Uses `/models` API shape; contains error handling, loading state, and confirm/cancel behavior.

- server/CHANGELOG_SUMMARY.md (this file) — newly added

## Commands run during this session

- Fixes and verification:
  - `python server/scripts/transcribe_uploads.py --use-gpu`
    - Result: model loaded to `cuda`, transcription completed, outputs written to:
      - `outputs/BRUDA_-_NIKAD_NE_DOVODI_ME_U_PITANJE/`
    - The previous UnicodeEncodeError was resolved by changing write calls to UTF-8.

- Environment packages:
  - `pip install nvidia-cuda-runtime-cu12` — installed the CUDA 12 runtime package via pip (for runtime compat).

## What was verified

- Device selection and GPU usage:
  - `whisper_loader.get_preferred_device` selects `'cuda'`/`'cuda:N'` when `WHISPER_FORCE_GPU` is set or when CUDA is available.
  - `transcribe_uploads.py` used the `whisper_loader` helper to load the converted checkpoint and successfully ran inference on GPU.

- Unicode output handling:
  - Output files are now written with explicit UTF-8 encoding, preventing `UnicodeEncodeError` on Windows (cp1250 default locale).

- Lion's Roar Studio modal:
  - `components/windows/ModelSelectorModal.tsx` displays model variations and provides selection callbacks to the app context. No code changes applied in this session; file was inspected as part of UI continuity checks.

## Known issues / Observations

- Transcription quality: the transcription result for the uploaded music file is noisy (likely expected for singing/music). Causes to consider:
  - The converted checkpoint may still have parameter mapping edge cases; check `models/whisper/.../mapping_report.json` for unmapped or partially-mapped parameters.
  - Tokenizer/processor mismatch (feature extractor / tokenizer files coming from the HF snapshot must be consistent with the converted checkpoint).
  - Whisper models typically perform better on spoken audio than singing; consider pre-processing (vocal isolation) before transcribing music.

## Next recommended steps

1. Run a deterministic Transformers vs Whisper comparison with a short TTS sample to isolate conversion fidelity from music domain noise. Use:

```powershell
python server/scripts/compare_transformers_vs_whisper.py --tts-text "The quick brown fox jumps over the lazy dog" --language en --use-gpu
```

2. Inspect the converter mapping report (`models/whisper/openai_whisper-large-v2/mapping_report.json`) and search for any unmapped keys (especially `encoder.ln_post` or `cross_attn_ln` variants). If unmapped keys exist, add targeted mapping rules in `convert_transformers_to_whisper.py` and re-run.

3. Optionally add a `--out-dir` CLI flag to `transcribe_uploads.py` for easier testing and CI integration.

4. If you need higher fidelity for sung vocals, run vocal separation first (`demucs`) and transcribe the isolated vocals track.

5. Add short unit/integration tests for the loader and the transcription writing behavior (mock whisper to avoid heavy model downloads during CI).

## Artifacts produced

- `outputs/BRUDA_-_NIKAD_NE_DOVODI_ME_U_PITANJE/` — transcription artifacts (txt/json/lrc/metadata)
- `models/whisper/openai_whisper-large-v2/model_converted.pt` — converted Whisper checkpoint (produced previously)
- `models/whisper/openai_whisper-large-v2/mapping_report.json` — converter mapping diagnostics

## Where to find changed code

- `server/scripts/transcribe_uploads.py` — UTF-8 writes + whisper_loader integration (modified)

## Follow-ups I can do for you

- Run the deterministic comparison to compute WER (recommended first).
- Summarize `mapping_report.json` and propose targeted mapping rules for any remaining unmapped parameters.
- Add `--out-dir` flag to `transcribe_uploads.py` and a small unit test.
- Improve log verbosity in `whisper_loader.py` to show `torch.cuda.device_count()` and chosen remapping when loading checkpoints.

---

If you'd like, tell me which follow-up you'd like to prioritize and I'll implement it and re-run the relevant tests. If you want the deterministic comparison run now, mention `--use-gpu` or `--cpu` preference.
