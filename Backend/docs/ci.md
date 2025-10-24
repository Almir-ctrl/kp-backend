# CI & Local Smoke Tests

This document explains the CI-safe mode used in this project, how to run smoke tests locally, and how to run full integration tests on self-hosted GPU runners.

## CI_SAFE mode (`CI_SMOKE`)

- The backend supports a CI-safe mode to keep CI fast and reliable. When `CI_SMOKE=true` is set, heavy ML models are not loaded. Instead, lightweight mocks/fallbacks are used for Whisper, MusicGen, Gemma, and other heavy processors.
- Use this mode for quick verification (lint, unit tests, smoke tests) in CI.

## Why this exists

- Large ML libraries (torch, torchaudio, demucs, transformers, etc.) are heavy and sometimes fail to build on hosted CI or require GPUs that aren't available. `CI_SMOKE` allows us to run a small subset of tests and smoke checks quickly, and keep CI green while preserving a path to run full integration tests on GPU hosts.

## Files of interest

- `scripts/smoke_test.py` — convenience script that hits `/health`, `/models`, `/gpu-status`, and `/songs` endpoints.
- `tests/` — contains tests marked with `ci_smoke` (see `pytest.ini` for the marker).
- `.github/workflows/smoke-test.yml` — CI workflow that runs lint and `ci_smoke` tests with `CI_SMOKE=true` and uploads test artifacts.
- `.github/workflows/integration-gpu.yml` — manual dispatch workflow to run full integration tests on self-hosted GPU runners.

## How to run smoke tests locally (PowerShell)

1. Open a PowerShell terminal.
2. Activate your Python virtual environment and install deps if needed:

```powershell
# from repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Set the CI_SMOKE environment variable and start the backend (optional - some tests start the app themselves):

```powershell
$env:CI_SMOKE = 'true'
python app.py
```

4. Run pytest to execute the `ci_smoke` marker and produce a junit xml artifact:

```powershell
$env:CI_SMOKE = 'true'
python -m pytest -q -m ci_smoke --junitxml=pytest_ci_smoke.xml
```

5. (Optional) Run the smoke script which exercises basic HTTP endpoints:

```powershell
$env:CI_SMOKE = 'true'
python scripts/smoke_test.py
```

## How to run smoke tests locally (bash / macOS / Linux)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CI_SMOKE=true
python app.py &
CI_SMOKE=true python -m pytest -q -m ci_smoke --junitxml=pytest_ci_smoke.xml
CI_SMOKE=true python scripts/smoke_test.py
```

## Manual GPU integration

- Use the `integration-gpu.yml` GitHub workflow to run the full test suite on a self-hosted runner labeled with `self-hosted,gpu`.
- The workflow is manual (workflow_dispatch) so you can trigger it when a GPU machine is available.

## Where outputs are stored

- Model outputs and artifacts are written to `outputs/{file_id}/`. Typical files include `transcription_base.json`, `transcription_base.txt`, `vocals.mp3`, `no_vocals.mp3`, and `metadata.json`.

## Viewing GitHub Actions results and artifacts

- After a CI run, the smoke-test workflow will upload the pytest junit xml (`pytest_ci_smoke.xml`) as an artifact. Download it from the Actions run page to review test results in JUnit-compatible viewers.
- The lint job artifacts (flake8 report) are also uploaded when available.

## Troubleshooting

- If tests fail with native extension import errors (e.g., torchaudio or other compiled libs), verify you're running with `CI_SMOKE=true` for smoke tests or use a GPU-run for full tests.
- If `/gpu-status` shows no GPUs and you expect one, ensure NVIDIA drivers and CUDA are installed and available to the Python environment (and that the process can access the GPU).

---

If you'd like, I can add example screenshots of the GitHub Actions artifact download and a small `CONTRIBUTING.md` snippet referencing this doc.
