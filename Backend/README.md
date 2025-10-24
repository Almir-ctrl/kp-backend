## AiMusicSeparator — Developer README



## Quick navigation


## Overview
The project is split into two areas:


New direction: a microservices prototype exists in this repo to isolate model workloads into separate containers, each pinning their own binary deps (Torch/CUDA). See `docker-compose.micro.yml`, `services/forward_auth/`, `services/demucs/`, `server/orchestrator.py`, and `nginx/`.


## Quickstart — Lion's Roar Studio
Requirements: Node.js 18+, npm (or yarn)

```bash
git clone <frontend-repo-url>
cd "lion's-roar-karaoke-studio"
npm install
npm run dev
# open http://localhost:3000
```

Configure API base URL in `src/constants.ts` or via `.env.local` (AI server URL must point to the orchestrator/backend).


## Quickstart — Backend (local venv)
Requirements: Python 3.11+, PowerShell on Windows, ffmpeg for media processing

```powershell
# From repo root (AiMusicSeparator-Backend)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py    # or python app_simple.py for a lightweight server
```

Health check once running:

```powershell
curl http://localhost:5000/health
```
Comprehensive developer README for the AiMusicSeparator project backend. This backend now acts as the orchestrator and API gateway for the modular microservices architecture. All model-specific code and documentation have been moved to the `/part of Backend/` directory.

---

## Quick Navigation
- Overview
- Quickstart (frontend)
- Quickstart (backend/orchestrator)
- part of Backend architecture
- Dev helpers (JWT, OpenAPI)
- Troubleshooting (Windows deps)
- CI & testing
- Migration checklist
- Contributing & support

---

## Overview
The project is now organized as follows:

- **Lion's Roar Studio:** `/Lion's Roar Studio/` — React + TypeScript app (Vite)
- **Backend:** `/Backend/` — Python-based orchestrator (Flask/FastAPI)
- **part of Backend:** `/part of Backend/` — Each AI model is a standalone service with its own code and documentation

**Model code and documentation:**
All model wrappers, guides, and technical docs are now in `/part of Backend/[model]/`. See `/part of Backend/README.md` for an overview and each subfolder's README for details.

---

## Quickstart — Lion's Roar Studio
Requirements: Node.js 18+, npm (or yarn)

```bash
git clone <frontend-repo-url>
cd "lion's-roar-karaoke-studio"
npm install
npm run dev
# open http://localhost:3000
```

Configure API base URL in `src/constants.ts` or via `.env.local` (AI server URL must point to the orchestrator/backend).

---

## Quickstart — Backend/Orchestrator (local venv)
Requirements: Python 3.11+, PowerShell on Windows, ffmpeg for media processing

```powershell
# From repo root (AiMusicSeparator-Backend)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py    # or python app_simple.py for a lightweight server
```

Health check once running:

```powershell
curl http://localhost:5000/health
```

If `pip install -r requirements.txt` fails due to C-extension builds on Windows, see "Troubleshooting" below.

---

## part of Backend prototype (local Docker Compose)
This repo contains a local microservices prototype to help isolate model workloads into separate containers, each pinning their own binary deps (Torch/CUDA). The prototype includes:

- `server/orchestrator.py` — minimal orchestrator (FastAPI)
- `services/demucs/` — Demucs prototype service (FastAPI)
- `services/forward_auth/` — small JWT validation service used by Nginx `auth_request`
- `nginx/` — gateway configuration that proxies to orchestrator and services
- `docker-compose.micro.yml` — dev compose file wiring everything

Bring it up locally (Docker Desktop required):

```powershell
# from repo root
docker compose -f docker-compose.micro.yml up --build
```

Create a short-lived test JWT for local dev (helper script in `scripts/`):

```powershell
python scripts/create_jwt.py supersecret123 > dev_jwt.txt
$TOKEN = Get-Content dev_jwt.txt

# Example: submit a Demucs job via Nginx gateway
curl -X POST http://localhost/demucs/jobs -H "Authorization: Bearer $TOKEN" -F "file=@./testdata/sample.mp3"
```

Notes:
- For production, recommendation is to use a queue (Redis / RabbitMQ) and per-service worker pools.
- Each model service should expose `/jobs`, `/jobs/{job_id}/status`, `/health` and a Prometheus `/metrics` endpoint.

---

## Dev helpers

- `scripts/create_jwt.py` — developer helper to create HS256 JWTs for local testing (short TTL). Use only for local dev.
- `dev/openapi/` — place OpenAPI YAML/JSON specs for orchestrator and each model service here.
- `dev/yaak/` — Yaak workspace exports to let developers import service definitions into the Yaak API client.

I can create a starter `dev/openapi/demucs.yaml` and `dev/yaak/demucs-workspace.json` if you want.

---

## Troubleshooting — Windows & binary dependencies
Some packages (e.g., `blis`, `av`, and certain PyTorch variants) require compiled binaries which are fragile on Windows. Recommended approaches:

1) Use Miniforge / conda-forge (recommended on Windows)

```powershell
& 'C:\Users\<you>\miniforge3\condabin\mamba.bat' env create -f environment.yml -n aimusic
& 'C:\Users\<you>\miniforge3\condabin\mamba.bat' activate aimusic
python -m pip install --no-deps audiocraft
# install additional pure-Python deps with pip as needed
```

2) If you must use pip/venv:
- Ensure Build Tools for Visual Studio are installed (cl.exe) and `ffmpeg` dev headers are available for `av`.
- If `blis` fails to build (unknown assembler flags like `-mavx512pf`), prefer conda-forge wheels or use an environment that already has a compatible `blis` binary.

3) GPU / PyTorch compatibility
- Each model service should pin one working combination of `torch` + CUDA in its Dockerfile. Audiocraft pins specific torch versions; mixing torch versions across services is one reason to separate services.

---

## CI & testing

- Keep CI jobs lightweight. Use an env var `CI_SMOKE=true` to enable CI-safe mode that uses mocked/fallback ML components.
- Suggested workflows:
  - `ci-basic.yml`: lint, unit tests, type checks
  - `ci-build-images.yml`: build docker images for services and push to registry
  - `ci-integration.yml`: run docker-compose micro stack and smoke test upload→process→notify
  - `full-stack-e2e.yml` (manual): start backend and frontend and run Playwright tests

Local smoke test (PowerShell example):

```powershell
$env:CI_SMOKE = 'true'
python -m pytest -q -m ci_smoke
```

---

## Migration checklist (short)

Phase 0 — Design
- Create OpenAPI definitions for orchestrator and each model service (store in `dev/openapi/`).
- Design storage layout and metadata schema for `outputs/{file_id}/metadata.json`.

Phase 1 — Prototype
- Implement Demucs prototype and orchestrator adapter. Validate locally with `docker-compose.micro.yml`.

Phase 2 — Queue & workers
- Replace HTTP push with queue (Redis/RabbitMQ), implement worker pools for GPU services.

Phase 3 — Scale & harden
- Add monitoring (Prometheus), tracing (OpenTelemetry), CI image builds, and staging cluster runs.

Phase 4 — Rollout
- Canary or blue/green deploy, monitor metrics and traces, then promote.

---

## Contributing

Follow the existing contributor workflow:

1. Create a branch with prefix `agent/` or `feat/`.
2. Add tests and update `dev/openapi/` if changing API shapes.
3. Run unit tests and smoke tests locally.
4. Open a PR referencing any companion frontend PRs if applicable.

---

## Support

- Issues & pull requests: use GitHub Issues/PRs
- For urgent infra incidents, consult `RECENT_SESSION_SUMMARY.md` and follow the secret-rotation and incident playbook in `.github/copilot-instructions.md`.

---

If you'd like I can now:
- Add starter OpenAPI and Yaak artifacts (`dev/openapi/demucs.yaml`, `dev/yaak/demucs-workspace.json`).
- Add `scripts/create_jwt.py` and `dev/README.micro.md` for local microservices dev.
- Run a quick lint pass on `services/forward_auth/forward_auth.py`, `services/demucs/app.py`, and `server/orchestrator.py`.

Tell me which next step you want me to take and I will do it.

   ### Prerequisites
   - Node.js 18+
   - npm or yarn

   ### Setup
   1. Clone the repo and install dependencies
   ```bash
   git clone <repository-url>
   cd "lion's-roar-karaoke-studio"
   npm install
   ```

   2. Copy the environment example and add keys
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local and set GEMINI_API_KEY and AI_SERVER_URL
   ```

   3. Start the dev server
   ```bash
   npm run dev
   ```

   4. Open http://localhost:3000

   ## Quick Start — Backend (AiMusicSeparator-Backend)

   ### Prerequisites
   - Python 3.11+
   - FFmpeg
   - (Optional) NVIDIA GPU + CUDA for model acceleration

   ### Setup
   1. Switch to the `server/` directory
   ```bash
   cd server
   ```

   2. Create and activate a virtual env
   ```bash
   # Windows
   python -m venv .venv
   .venv\\Scripts\\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   3. Install Python dependencies
   ```bash
   pip install -r requirements.txt
   ```

   4. Run the server
   ```bash
   python main.py
   ```

   5. Health check
   ```bash
   curl http://localhost:5000/health
   ```

   ## Project structure

   ```
   lion's-roar-karaoke-studio/
   ├── components/                # React components (frontend)
   │   ├── ui/
   │   └── windows/
   ├── context/                   # App context and global state
   ├── server/                    # Flask backend (AiMusicSeparator-Backend)
   │   ├── main.py
   │   ├── requirements.txt
   │   └── README.md              # Backend-specific docs
   ├── utils/                     # Utility scripts
   ├── public/                    # Static assets
   ├── index.css                  # Tailwind CSS
   ├── App.tsx                    # React application entry
   └── package.json               # Node dependencies
   ```

   ## Configuration

   ### Environment (frontend)
   ```
   # .env.local
   GEMINI_API_KEY=your_gemini_api_key_here
   AI_SERVER_URL=http://localhost:5000
   ```

   ### Environment (backend `.env` / server config)
   ```
   DEBUG=False
   SECRET_KEY=your-super-secret-key
   HOST=0.0.0.0
   PORT=5000
   DEMUCS_MODEL=htdemucs
   WHISPER_MODEL=base
   MUSICGEN_MODEL=small
   MAX_CONTENT_LENGTH=104857600
   ```

   ## Advanced usage

   - Use `server/` endpoints to run processing tasks, e.g. `/process/demucs`, `/process/whisper/<file_id>`, `/process/musicgen/<session_id>`.
   - WebSocket endpoints are available for real-time streaming and transcription.
   - See `server/README.md` for full backend API examples and deployment options.

   ## Contributing

   1. Fork the repo
   2. Create a feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
   3. Commit and push
   ```bash
   git commit -m "Add amazing feature"
   git push origin feature/amazing-feature
   ```
   4. Open a pull request

   ## License

   This project is licensed under the MIT License — see the `LICENSE` file for details.

   ## Support & Acknowledgments

   - Support: support@lionsroar.studio
   - Acknowledgments: Demucs, OpenAI Whisper, MusicGen, Google Gemma, Librosa, React, Vite, Tailwind

   ---

   <div align="center">
   <p><strong>🦁 Made with ❤️ for karaoke enthusiasts worldwide</strong></p>
   <p><em>Unleash your inner lion and roar with confidence!</em></p>
   </div>
This project is licensed under the MIT License - see the [LICENSE](Frontend\LICENSE) file for details.

## 🙏 Acknowledgments

- **Demucs**: AI-powered source separation by Meta Research
- **OpenAI Whisper**: Robust speech recognition system
- **Google Gemini**: Advanced AI for vocal coaching features
- **React & Vite**: Modern web development framework
- **Tailwind CSS**: Utility-first CSS framework

## 🆘 Support

### Troubleshooting

**Lion's Roar Studio Issues:**
- Ensure Node.js 18+ is installed
- Clear browser cache and restart dev server
- Check browser console for error messages

**Backend Issues:**
- Verify Python 3.8+ and ffmpeg are installed
- Check server health at `http://localhost:5000/health`
- Review server console for dependency errors

**Performance Tips:**
- Use NVIDIA GPU with CUDA for faster AI processing
- Close unused applications during AI processing
- Ensure sufficient disk space (4GB+ recommended)
- Transcription with timestamps works best with clear audio
- Use high-quality audio files for better lyric accuracy
- Vocal separation works best with stereo recordings
- Confirm processing choices as vocal separation replaces original songs

### Getting Help
- 📧 **Email**: [support@lionsroar.studio](mailto:support@lionsroar.studio)
- 🐛 **Bug Reports**: [Create an Issue](https://github.com/your-repo/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

---

<div align="center">
<p><strong>🦁 Made with ❤️ for karaoke enthusiasts worldwide</strong></p>
<p><em>Unleash your inner lion and roar with confidence!</em></p>
</div>
 
## Developer notes — Lint & Test cleanup (Batch 2)

Brief summary of recent maintenance performed on the backend repository:

- Ran a repo-wide lint pass (flake8) with max-line-length = 100 and fixed
   style issues across medium-sized modules.
- Modernized many tests to pytest style and added guarded skips for tests
   that require heavy native model dependencies (Essentia, large ML libs).
- Made heavy optional dependencies (Essentia, scikit-learn, matplotlib)
   optional at runtime. Code paths now either lazy-import or fall back to
   safe defaults when those packages are not installed so CI and local
   dev runs remain fast and reliable.

Verification results

- flake8: clean (run with: python -m flake8 . --max-line-length=100)
- pytest: 52 passed, 8 skipped (full run performed during cleanup)

Optional-deps guidance

- If you require advanced features (HPCP via Essentia, clustering via
   scikit-learn, or plotting via matplotlib), install those packages in
   your environment. Example:

```powershell
pip install essentia scikit-learn matplotlib
```

- If you'd like, I can add a `requirements-optional.txt` or update
   documentation with a developer setup script to install these extras.

## CI smoke tests & GPU-only policy

- CI-safe mode (CI_SMOKE): the backend supports a CI-safe mode that avoids loading heavy ML models and instead uses small mocks/fallbacks for Whisper, MusicGen and other processors. CI jobs that must remain fast and reliable set the environment variable `CI_SMOKE=true`.

- How CI uses it: the GitHub Actions smoke-test workflow sets `CI_SMOKE=true` so the pipeline runs a focused test subset marked `ci_smoke` and uses light-weight mocks. A separate manual workflow (`integration-gpu.yml`) exists to run full integration tests on self-hosted GPU runners (see `.github/workflows/integration-gpu.yml`).

- Running smoke tests locally (PowerShell):
   - Start the backend in one terminal (optional, some tests spin up the app):
      $env:CI_SMOKE = 'true'
      python app.py
   - In another terminal run the pytest marker for smoke tests and produce a junit xml:
      $env:CI_SMOKE = 'true'; python -m pytest -q -m ci_smoke --junitxml=pytest_ci_smoke.xml

- Running smoke tests locally (bash / macOS / Linux):
   - Start backend (optional):
      export CI_SMOKE=true
      python app.py
   - Run smoke tests:
      CI_SMOKE=true python -m pytest -q -m ci_smoke --junitxml=pytest_ci_smoke.xml

- Smoke script: a convenience script `scripts/smoke_test.py` is provided to hit basic endpoints (health, models, gpu-status, songs). When running the script locally with the backend up, set `CI_SMOKE=true` to exercise CI-safe behaviour.

- GPU-only policy ("NIKADA CPU"): heavy inference is protected by a GPU guard. Processors that require CUDA will raise a clear error when a GPU is not available. The REST endpoint `/gpu-status` provides a pre-flight check (GET `/gpu-status`) that returns JSON with GPU availability and CUDA / torch information so clients can fail fast before submitting heavy jobs.

- Outputs location: model outputs and artifacts are written under `outputs/{file_id}/` (for example `outputs/<uuid>/transcription_base.json`, `transcription_base.txt`, `vocals.mp3`, `no_vocals.mp3`, and `metadata.json`). Use this directory when inspecting generated artifacts after a run.

If you want me to also add a short `CONTRIBUTING.md` snippet or a dedicated `docs/ci.md` with example screenshots of the GitHub Actions job results, I can add that next.
