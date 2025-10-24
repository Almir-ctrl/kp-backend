# Cross-repo collaboration (backend ↔ frontend)

Purpose
- Document a lightweight, repeatable workflow for proposing API changes, coordinating PRs across the backend and frontend repositories, and running local integration checks.

When to use
- Any change to backend endpoints, request/response shapes, or behavior that the frontend depends on.

Quick flow
1. Update `api/openapi.yaml` in the backend repo with the new/changed contract.
2. Add a short entry in `server/CHANGELOG.md` describing the change and the frontend impact.
3. Create a backend PR that implements the change and references the OpenAPI update and changelog entry.
4. Create a frontend PR that updates the client code to match the new contract (generate types from `api/openapi.yaml` or update manual types).
5. Link the two PRs in each other's description and add the label `frontend-impact`.
6. Run local integration tests (instructions below) and add the results to PR checks or comments.
7. Merge both PRs when tests pass and stakeholders approve.

PR checklist for backend changes that affect frontend
- [ ] Update `api/openapi.yaml` (or add an example request/response in the changelog)
- [ ] Add `server/CHANGELOG.md` entry describing frontend impact (endpoints, example payloads)
- [ ] Add/adjust unit and integration tests (`test_*.py`) to cover the new contract
- [ ] Create or update a frontend PR and link it here (include example client snippet)
- [ ] Add labels: `frontend-impact`, `needs-approval` (optional)
- [ ] If breaking change, include a migration note and a suggested deadline for frontend upgrade

Local development tips
- Run backend locally and point frontend dev server to `API_BASE_URL=http://127.0.0.1:5000`.
- If frontend cannot tolerate CORS changes, run `python server/proxy_audio.py` (proxy example) or enable dev-only CORS in the backend.
- Use the `api/openapi.yaml` to generate client types:
  ```bash
  # example with openapi-generator (frontend repo)
  openapi-generator-cli generate -i ../Backend/api/openapi.yaml -g typescript-fetch -o src/api
  ```
- For quick mocking, copy example responses from `server/CHANGELOG.md` or the OpenAPI `examples` into a small mock server (json-server or Flask) and point frontend at it.

CI guidance (template idea)
- In PRs labeled `frontend-impact`, run an integration job that:
  1. Starts the backend (docker or `python Backend/app.py`).
  2. Runs a small smoke test script that exercises the changed endpoints.
  3. Optionally, kick off the frontend build and run a smoke test against it.

Optional next steps (I can implement)
- Add `.github/workflows/integration-example.yml` template that starts the backend and runs a smoke test.
- Provide a small `integration-tests/` script that runs curl checks (upload → process → status → download) using a test fixture.

If you'd like, I can now add the optional CI workflow template and a tiny smoke test script; tell me and I'll create them in the repo.
