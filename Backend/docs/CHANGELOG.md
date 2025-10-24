# 2025-10-21 — Advanced CI + duplicate-upload flow + frontend jsdom guards

	- `.github/workflows/ci-basic.yml` — minimal baseline checks (TS check, unit tests, pytest)
	- `.github/workflows/ci-fast.yml` — faster matrixed checks including mocked Playwright E2E and caching
	- `.github/workflows/full-stack-e2e.yml` — manual workflow to start backend and run full Playwright E2E

	- `AiMusicSeparator-AI separator backend/tests/test_upload_duplicate.py` — pytest that posts the same file twice and asserts 409 and response shape
	- `lion's-roar-karaoke-studio/src/__tests__/duplicateUpload.test.tsx` — Jest test that mocks 409 response and validates frontend behavior

	- Added import-time guards in `context/AppContext.tsx` and `components/ControlHub.tsx` to avoid DOM access on import
	- Added `test:unit` / `test:dom` npm scripts for running Node-based unit tests and jsdom tests separately




See `RECENT_SESSION_SUMMARY.md` for a full breakdown and next steps.

### 2025-10-22 — Enforce GPU-only inference + /gpu-status probe

- Added backend helper `require_gpu_or_raise()` which prevents CPU fallback for heavy AI models (Demucs, Whisper, MusicGen, Gemma3N). This makes model processing strict GPU-only (user requirement: "NIKADA CPU").
- Added new endpoint `GET /gpu-status` which returns lightweight information about PyTorch/CUDA availability and GPU devices for safe frontend pre-flight checks. The endpoint does not load large models.
- Updated `/process/<model>/<file_id>` and separation flows to fail-fast with HTTP 503 when a GPU is not available. Clients should call `/gpu-status` prior to submitting heavy processing requests and handle 503 responses gracefully.
- Lion's Roar Studio: Added Direct Whisper Console in the Lion's Roar UI which calls `/gpu-status` before submitting transcription requests and displays transcriptions inline with improved visuals (spinner, larger panel). Also applied UI polish (larger player controls, premium styling in karaoke tabs).

Notes:
- If deploying on machines without CUDA-capable GPUs, the backend will now return 503 for heavy model requests; add deploy-time checks or run a mock-mode if required for CI.
# 2025-10-21
## Dockerfile, Compose, and Dependency Modernization
- Dockerfile now uses CUDA 13.0.1-cudnn-devel-ubuntu24.04 as base image for latest GPU support.
- PyTorch and torchvision are installed from the nightly cu130 index (no version pinning) for maximum compatibility with new GPUs.
- transformers upgraded to >=4.39.0 in requirements for Gemma2/Gemma3N model support.
- Added Docker Compose v2.40+ `watch` section for hot-reload/live sync (commented out for build compatibility).
- Removed `version:` field from docker-compose.dev.yml to enable `watch` property.
- Documented workaround for PEP 668 (externally managed environment) using `--break-system-packages` in pip install commands.
- Clarified all Python/transformers installs must be inside the Docker container, not just on the host.
## sync_torch_cuda.ps1: pip/pip3 Compatibility
- Added logic to detect and use either `pip` or `pip3` for all install commands in `scripts/sync_torch_cuda.ps1`.
- Ensures compatibility on systems where only `pip3` is available.
- All install steps (PyTorch Nightly, requirements.txt) now work with either command.

### 2025-10-23 — CI workflow improvements

- Added `lint` job in `.github/workflows/smoke-test.yml` to run flake8 early and provide faster feedback.
- Added pip cache to the smoke-test job to accelerate dependency installation.
- Set `CI_SMOKE=true` in the smoke-test job so CI uses lightweight mocks/stubs for heavy models (avoids GPU and large weight downloads).
- Added a cleanup step that attempts to stop the background backend process at the end of the smoke job.
