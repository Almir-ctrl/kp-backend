# Container verification notes — Backend path normalization

Date: 2025-10-24
Branch: feat/normalize-backend-container

Summary:
- Verified container runtime files (Dockerfiles under project root and `Backend/deployment/`, and `docker-compose.watch.yml` variants) reference the application using the capitalized `Backend/` path (for example: `ENV FLASK_APP=Backend/app.py` and compose commands using `python Backend/...`).

What I checked:
- `Dockerfile`, `Dockerfile.simple`, `Backend/deployment/Dockerfile*` — `ENV FLASK_APP=Backend/app.py` set.
- `docker-compose.watch.yml` (root, `Frontend/`, `Backend/deployment/`) — service `command` and `healthcheck` reference `Backend/server/worker.py` and `Backend/server/backend_skeleton.py`.

Recommendation / next steps:
1. Build and run the compose watch stack locally and validate the backend process is started from `/app/Backend` and health endpoints respond.
2. If CI still reports missing `backend/requirements.txt`, check the failing workflow's working directory and runner logs for any lingering lowercase `backend/` references in workflow steps or cached actions.
3. If a change to the image layout is needed in future, update the specific Dockerfile's `WORKDIR` or `ENV PYTHONPATH` and rebuild the affected images.

Quick local smoke test (PowerShell):
```powershell
# From repository root
docker compose -f .\docker-compose.watch.yml build
docker compose -f .\docker-compose.watch.yml up -d
docker compose -f .\docker-compose.watch.yml ps
docker compose -f .\docker-compose.watch.yml logs -f watcher
# Check backend health endpoint (adjust port if needed)
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

This file was added to document container-level verification for reviewers and CI.
