# part of AI separator backend refactor — full plan (frontend + backend)

This document is a comprehensive, actionable guide to refactor the AiMusicSeparator project into a secure, production-ready microservices architecture with a single orchestrator. It covers architecture, service responsibilities, API contracts, orchestration, storage, auth, tracing, CI/CD, testing, migration steps, rollback, monitoring and operational runbook items.

Save this file and follow the staged "Migration checklist" near the end. Keep the OpenAPI files in `dev/openapi/` and Yaak workspace exports in `dev/yaak/` as you implement services.

---

## 1 — Goals and non-goals
- Goals
  - Isolate heavy AI workloads into model-specific services (Demucs, Whisper, MusicGen, PitchAnalysis, Gemma3N).
  - Keep a single orchestrator (current backend) for authentication, job submission, status aggregation, storage metadata, and UI-facing API.
  - Allow per-service dependency/version pinning (e.g., GPU drivers & Torch versions) so different services can use different CUDA/Torch combos.
  - Provide secure boundaries (JWT or mTLS), traceability (request IDs), and robust job lifecycle (queueing, retries).
  - Make local dev easy (docker-compose) and production deployable (Kubernetes / managed services).
- Non-goals
  - Replace frontend features or change UX unless needed by new API shapes.
  - Commit to any single production infra provider; recommendations are provided.

## 2 — High-level architecture

- Components
  - Orchestrator (current backend): HTTP API for frontend, job metadata store, coordinator. Responsible for authentication, job routing, storage ACLs, and exposing `/status/{file_id}` and `/songs`.
  - Model microservices: HTTP (or worker) services for each model type:
    - Demucs service (audio separation) — GPU node pool.
    - Whisper service (transcription) — CPU/GPU depending on variation.
    - MusicGen service (generation) — GPU node pool.
    - PitchAnalysis service — CPU.
    - Gemma3N service (lyrics/align) — GPU where needed.
  - Storage: centralized object store (S3/GCS/MinIO) or shared filesystem for dev (`uploads/` and `outputs/`).
  - Queue/broker: Redis/RabbitMQ/Kafka (recommended) for job submissions and backpressure.
  - Gateway / ingress: NGINX (or Traefik) + `auth_request` for JWT verification; use a gateway for TLS, rate limiting, and routing.
  - Dev tooling: Yaak (desktop API client) for API tests / OpenAPI consumption.

- Data flow (request example)
  1. User uploads file → Orchestrator stores file (S3 or `uploads/`) and responds with `file_id`.
  2. Lion's Roar Studio calls Orchestrator `POST /process?model=demucs&variation=...` → orchestrator enqueues job and returns `job_id`.
  3. Worker service (Demucs) picks job from queue (or gets HTTP push) and fetches file (pre-signed URL or shared path).
  4. Demucs runs, writes outputs to `outputs/{file_id}/demucs/` or uploads to S3 and posts callback to Orchestrator `/notify`.
  5. Orchestrator updates job metadata and `status`. Lion's Roar Studio polls `/status/{file_id}` or uses websocket to receive updates.

## 3 — Service boundaries & responsibilities

- Orchestrator responsibilities
  - Authentication / Authorization (JWT/OAuth introspection).
  - Job metadata management and status aggregation.
  - Store file metadata and host presigned upload/download URLs.
  - Submit jobs to model services (via queue or HTTP).
  - Accept model service callbacks: `/notify` with job_id, file_id, outputs[].
  - Provide UI-safe endpoints, e.g., `/upload`, `/process`, `/status/{file_id}`, `/models`, `/songs`.
  - Provide admin API for model provisioning, cancelation, and retries.

- Model service responsibilities
  - Accept job payload (file URL or file_id + presigned URL or local path).
  - Validate payload and run the model.
  - Write outputs to storage with a predictable output path (e.g., `outputs/{file_id}/{model}/...`).
  - Emit progress events (via broker or HTTP progress: `/jobs/{id}/progress`).
  - Post completion callback to Orchestrator with status and outputs (or publish to broker topic).
  - Expose `GET /health` and optionally `/metrics`.

- Lion's Roar Studio responsibilities
  - Only talk to the Orchestrator (not to model services directly) for consistent auth and metadata.
  - Poll or subscribe to status updates (via websockets or server-sent events).
  - Handle duplicate detection response codes (409) per backend spec.
  - Use Yaak or other API client to test model APIs during development.

## 4 — Authentication, authorization, and network security

- Authentication
  - Use JWTs signed by a trusted IdP (preferred) or produce short-lived JWTs from Orchestrator for internal communication.
  - For frontend → Orchestrator: use OAuth 2.0 / JWT access tokens or session tokens proxied by Orchestrator.
  - For Orchestrator → Model services: prefer mTLS (mutual TLS) in K8s or signed JWTs with short TTL; mTLS/Gateway-level auth provides stronger guarantees.

- Authorization
  - Orchestrator enforces user-level authorization (ensure the user can process that file_id).
  - Model services only accept jobs from Orchestrator; enforce by validating token or mTLS client cert.

- Gateway & ingress
  - Use NGINX (or Traefik) as ingress for TLS termination and to perform `auth_request` to a JWT validation service (`forward-auth`) that returns 2xx for valid tokens.
  - For internal traffic, use mTLS or private VPC networking.

- Secrets
  - Store secrets in Vault, AWS Secrets Manager, or GitHub Actions secrets for CI.
  - Never store private keys or long-lived secrets in repo or environment variables in CI logs.

## 5 — Tracing, logging & request IDs
- Propagate `X-Request-ID` from frontend through Orchestrator to model services and store it in logs for correlation.
- Use structured JSON logs and centralize them (ELK/CloudWatch/Datadog).
- Add distributed tracing (OpenTelemetry) for request flows; sample traces for long-running jobs are especially useful.

## 6 — Storage design (uploads / outputs)
- Production: Use S3/GCS with versioned buckets, lifecycle policies, and TTL for temporary outputs.
  - Upload pattern: Lion's Roar Studio requests `POST /upload` → Orchestrator returns pre-signed `PUT` URL; frontend uploads file directly to S3.
  - Model services use pre-signed `GET/PUT` or mounted object storage SDK to download inputs and upload outputs.

- Dev/local: `uploads/` and `outputs/` directories mounted into services (docker-compose).

- Output layout (recommended)
  - outputs/{file_id}/
    - metadata.json
    - demucs/
      - vocals.mp3
      - no_vocals.mp3
    - whisper/
      - transcription.txt
      - segments.json

- Metadata file (`outputs/{file_id}/metadata.json`) should include:
  - original_filename, uploaded_by, created_at, mime_type, duration, sample_rate, request_ids, processing steps completed.

## 7 — Job lifecycle and states
- Standard job states:
  - queued
  - running
  - progress (percent + message)
  - completed (success)
  - failed (with error info)
  - canceled
- Retry policy:
  - Retry transient errors (exponential backoff, caps).
  - Persistent errors require manual inspection and routing to admin UI.
- Idempotence
  - Model services should detect and handle duplicate jobs for same `file_id` to avoid re-processing (orchestrator should check outputs existence and skip jobs).

## 8 — Queue vs direct HTTP
- Queue (recommended for production)
  - Use Redis streams, RabbitMQ, or cloud-managed queues (SQS).
  - Benefits: backpressure handling, retries, persistent jobs if worker restarts.
- HTTP push (simpler for prototyping)
  - Orchestrator performs HTTP POST to model service; model service processes and calls back.
  - Easier to implement but less robust under load.

## 9 — API contracts (summary) — orchestrator & model service

High-level shapes. Use these for OpenAPI definitions.

- Orchestrator endpoints (frontend → orchestrator)
  - POST /upload
    - returns: { file_id, upload_url (presigned), expires_at }
  - POST /process
    - body:
      - file_id
      - model: 'demucs'|'whisper'|'musicgen'|'pitch'|'gemma3n'
      - variation: string (optional)
      - params: object (optional)
    - response: { job_id, status: 'queued' }
  - GET /status/{file_id}
    - returns consolidated job statuses and outputs
  - POST /notify (model service → orchestrator)
    - body: { job_id, file_id, model, status: 'completed'|'failed', outputs: [ {path, url, type} ], logs_url? }

- Model service endpoints
  - POST /jobs
    - body: { job_id (optional), file_id, file_url (or presigned GET URL), variation, params, callback_url }
    - response: { job_id, status: 'accepted' }
  - GET /jobs/{job_id}/status
    - response: { job_id, status, progress, started_at, finished_at, outputs[] }
  - GET /health
    - response: { status: 'ok', version, gpu: bool, queue: ... }

Example minimal OpenAPI fragment for Demucs service (YAML-ish)
```yaml
openapi: 3.0.3
info:
  title: Demucs Service API
  version: 0.1.0
paths:
  /jobs:
    post:
      summary: Create demucs job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                file_id: { type: string }
                file_url: { type: string }
                variation: { type: string }
                callback_url: { type: string }
      responses:
        '200':
          description: Job accepted
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id: { type: string }
                  status: { type: string }
  /jobs/{job_id}/status:
    get:
      parameters:
        - name: job_id
          in: path
          required: true
          schema: { type: string }
      responses:
        '200':
          description: Job status
          content:
            application/json:
              schema:
                type: object
```

(Produce full OpenAPI files per service in `dev/openapi/` during implementation.)

## 10 — Lion's Roar Studio changes
- Only talk to the Orchestrator: All job orchestration and authorization happens here. Example flow:
  1. `POST /upload` → get presigned `PUT` URL.
  2. Upload file directly to object store with the presigned URL.
  3. `POST /process` with `file_id` and `model`.
  4. Poll `/status/{file_id}` or subscribe to notifications via websocket.
  5. Handle `409 Conflict` and `skipped` responses (existing outputs) — switch UI to existing file.

- Duplicate detection: Orchestrator must return `409` with `{ "error":"Song already exists", "file_id":"..." }` when duplicate upload is detected.

- SDKs: Create a small frontend SDK that wraps the Orchestrator endpoints, handles token injection, and provides a simple Promise-based interface and progress events.

- CORS: Orchestrator should set CORS and `Access-Control-Expose-Headers` to include `X-Request-ID`.

## 11 — AI separator backend (orchestrator) changes — implementation details
- Add a `jobs` table (Postgres or SQLite for prototype) with fields:
  - job_id, file_id, model, variation, status, progress, created_at, started_at, finished_at, outputs (JSON), request_id, user_id.
- Implement an adapter layer to submit jobs:
  - `submit_job(model, file_id, variation, params)` → enqueues job (queue) or sends HTTP request.
- Add webhook/callback endpoint: `/notify` that model services call.
- Implement skip logic: `check_output_exists(file_id, output_type)` to avoid reprocessing.
- Implement administrative endpoints: `/admin/jobs/{job_id}/retry`, `/admin/jobs/{job_id}/cancel`.
- Ensure Orchestrator accepts incoming `X-Request-ID` and returns it via `Access-Control-Expose-Headers`.

## 12 — Model service implementation checklist (per service)
- Container image building with pinned dependencies (Torch versions per service).
- Entrypoints:
  - `/health`, `/jobs`, `/jobs/{job_id}/status`
- Use the same storage path convention `outputs/{file_id}/{model}/`.
- Support callback_url in job request or use broker topic if using queue.
- Provide GPU selection and concurrency control (max concurrent jobs).
- Provide metrics (/metrics Prometheus).
- Implement graceful shutdown and checkpointing for long jobs.

## 13 — Local dev & docker-compose
- Provide `docker-compose.micro.yml` for quick prototyping (we created one in repo).
- Development pattern:
  - Orchestrator runs on host port (e.g., orchestrator.local or http://localhost:5000).
  - Nginx gateway listens on `localhost:80` and forwards to orchestrator/demucs.
  - `forward-auth` validates JWTs for `/auth/verify`.
- Example run: (from repo root)
```bash
# build images and bring up prototype locally
docker compose -f docker-compose.micro.yml up --build
```
- Make sure `./uploads` and `./outputs` exist and are writable.

## 14 — CI/CD recommendations
- Jobs to add:
  - Lint + unit tests for each microservice.
  - Build & test Docker images (use multi-stage to keep image size small).
  - Integration smoke test: run docker-compose in CI (or run in GitHub Actions runner) and execute a sample upload → process → status flow using mocks for heavy models.
  - Security scans (trivy) for container images.
  - Deploy pipelines:
    - Staging: push images, run K8s update in a staging cluster (or rollout on cloud provider).
    - Production: require manual promotion and run canary deployments.

- Example CI flow (GitHub Actions)
  - `ci-lint.yml` for lint/test
  - `ci-build-images.yml` to build and push images to registry
  - `ci-integration.yml` to run integration smoke tests with docker-compose

## 15 — Testing strategy
- Unit tests: each service should have unit tests for small helpers.
- Contract tests: generate OpenAPI client tests to ensure orchestrator and model service expectations match.
- Integration smoke tests: a test that:
  - Starts a minimal stack (orches., demucs stub) and performs:
    - Upload simulation
    - POST /process for demucs
    - Poll /status until complete
    - Validate output files exist and metadata written.
- E2E: run against staging cluster with real models (slow).
- Test for edge cases: missing inputs, duplicate uploads, long-running jobs cancellation, network interruption.

## 16 — Observability & monitoring
- Metrics:
  - Job counts by status, job latency, GPU utilization per model, queue depths.
  - Expose `/metrics` Prometheus endpoint on each service.
- Tracing:
  - Use OpenTelemetry instrumentation and sample spans for a job lifecycle.
- Logs:
  - Structured JSON logs with fields: timestamp, job_id, file_id, model, level, message, request_id, user_id.
- Alerts:
  - Alert on high queue depth, repeated job failures, out-of-disk errors, OOMs on GPU nodes.

## 17 — Deployment & scaling recommendations
- Use Kubernetes for production:
  - Use separate node pools for GPU services (taints/tolerations).
  - Use HorizontalPodAutoscaler for stateless services; for GPU jobs use a job queue and worker pods scaled based on queue length.
- Use durable storage for outputs (S3) and a shared DB (Postgres) for metadata.
- Rolling upgrades: deploy new images with canary or blue/green; ensure job compatibility between orchestrator and model service before rolling.

## 18 — Security & compliance
- Network isolation: place model services in private subnets; only orchestrator & API gateway exposed.
- Secrets: rotate regularly; store in secret manager and grant least privilege.
- Authentication: prefer OIDC if integrating with an identity provider; JWTs verified with JWKS.
- mTLS: for inter-service auth consider mTLS (mutual TLS) in K8s via service mesh (Istio) or via Linkerd.
- RBAC: admin endpoints protected and only available to admin users.
- Data retention & privacy: define retention policies for uploads and outputs; encrypt S3 buckets and secure backups.

## 19 — Migration plan (staged, safe, verifiable)
This is the recommended step-by-step plan to refactor with minimal downtime.

Stage 0 — Design + tests
- Document API contracts and OpenAPI specs for orchestrator and each model service. (store in `dev/openapi/`)
- Add `dev/yaak` workspace exports to let developers test endpoints locally.
- Decide queue (Redis/RabbitMQ) and storage (S3/MinIO) provider.

Stage 1 — Prototype & dev
- Implement a lightweight Demucs microservice (stub or lightweight version).
- Implement `docker-compose.micro.yml` (we have one) and ensure local dev flow works: upload → process → outputs created.
- Validate the handshake: orchestrator → demucs → callback.

Validation checks:
- Upload route returns presigned URL or `file_id`.
- `POST /process` returns job_id and enters `queued`.
- Model service runs and posts callback to `/notify`.
- `GET /status/{file_id}` aggregates statuses.

Stage 2 — Model services & queue
- Replace HTTP push with queue (Redis/RabbitMQ).
- Add one real GPU-backed Demucs worker that picks up jobs from queue.
- Validate with real model on staging.

Stage 3 — Build out other services
- Implement Whisper, MusicGen, PitchAnalysis, Gemma3N following the same template.
- Add per-service Dockerfiles and pin dependencies.

Stage 4 — Hardening & deployment
- Add monitoring, tracing, and alerting.
- Add CI pipelines and image scanning.
- Deploy to staging cluster and run e2e tests.

Stage 5 — Production rollout
- Gradual rollout via canary or blue/green.
- Monitor success and rollback if major errors are observed.
- Deprecate old monolithic endpoints only after clients verified.

Rollback steps
- If new orchestrator changes cause failures:
  - Route traffic back to previous orchestrator version (rollback image).
  - Re-queue failed jobs or leave them in queue for new worker to pick up.
- If model worker has incompatible outputs:
  - Keep previous image available and fallback to previous worker replicaset.

## 20 — Operations / runbook (incident response)
- Slack pager playbook for critical alerts (high failures/queue backlog).
- Step 1: check orchestrator health and DB.
- Step 2: check queue depth and worker logs.
- Step 3: check storage availability (`outputs` bucket) and disk usage.
- Step 4: rollback the last deployment if severity high and repeatable.
- Postmortem: record root cause, mitigation, and change to prevent recurrence.

## 21 — Cost & capacity planning
- Estimate based on model runtimes:
  - Demucs: moderate GPU use per track (~minutes per song depending on model).
  - MusicGen / Gemma3N: heavy GPU use (can be expensive).
- Use spot instances for batch processing where acceptable, and reserved for low-latency live processing.
- Monitor GPU runtime vs queue backlog and provision autoscaling accordingly.

## 22 — Developer experience (DX)
- Provide `dev/README.md` with:
  - `docker compose -f docker-compose.micro.yml up --build` example
  - How to create a test JWT:
    ```bash
    python - <<'PY'
    import jwt, time
    payload = {"sub":"dev-user","iat":int(time.time()),"exp":int(time.time())+3600}
    print(jwt.encode(payload,"supersecret123",algorithm="HS256"))
    PY
    ```
  - Example curl to create job:
    ```bash
    TOKEN=eyJ... # created above
    curl -X POST http://localhost/demucs/jobs \
      -H "Authorization: Bearer $TOKEN" \
      -F "file=@/path/to/song.mp3"
    ```
- Provide Yaak workspace (`dev/yaak/`) with the OpenAPI imports for each service so developers can click-and-play.

## 23 — Example: minimal orchestrator → demucs job flow (curl)
- Create JWT (as above).
- Create job via orchestrator (example; orchestrator should accept file_id or presigned url):
```bash
curl -X POST http://localhost/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_id":"<file-id>", "model":"demucs", "variation":"default"}'
```
- Poll status:
```bash
curl http://localhost/status/<file_id> -H "Authorization: Bearer $TOKEN"
```

## 24 — Testing checklist before production
- Unit tests: all services (>=90% for critical code).
- Integration: orchestrator + demucs worker (docker-compose) smoke tests.
- E2E: staging test with realistic audio files (validate outputs and metadata).
- Security tests: ensure JWT validation works and services reject unauthorized requests.
- Performance tests: simulate concurrency to understand job time and GPU requirements.

## 25 — Example repository layout and files to add
- dev/
  - openapi/
    - orchestrator.yaml
    - demucs.yaml
    - whisper.yaml
  - yaak/
    - demucs-workspace.json
- services/
  - demucs/ (service code + Dockerfile + tests)
  - whisper/
  - musicgen/
  - forward_auth/
- server/
  - orchestrator.py (or existing `app.py` extended)
- infra/
  - k8s/
    - demucs-deployment.yaml
    - orchestrator-deployment.yaml
  - terraform/ (optional for infra)
- docker-compose.micro.yml (dev compose file)
- docs/MICROSERVICES_REFACTOR.md (this document)
- scripts/
  - create_jwt.py (dev helper to create JWT)
  - smoke_test.sh

## 26 — Appendix — small snippets & helpers

- Simple JWT creation helper (Python)
```python
# scripts/create_jwt.py
import jwt, time, sys
secret = sys.argv[1] if len(sys.argv)>1 else "supersecret123"
payload = {"sub":"dev-user","iat":int(time.time()),"exp":int(time.time())+3600}
print(jwt.encode(payload, secret, algorithm="HS256"))
```

- Example model callback payload (POSTed to orchestrator `/notify`)
```json
{
  "job_id": "1234-demucs",
  "file_id": "1234",
  "model": "demucs",
  "status": "completed",
  "outputs": [
    {"path": "outputs/1234/demucs/vocals.mp3", "url": "https://s3/.../vocals.mp3", "type": "vocals"},
    {"path": "outputs/1234/demucs/no_vocals.mp3", "url": "https://s3/.../no_vocals.mp3", "type": "no_vocals"}
  ],
  "request_id": "req-uuid",
  "duration_seconds": 240
}
```

## 27 — Migration checklist (actionable)

Phase A — Planning (Do not skip)
- [ ] Write OpenAPI specs for orchestrator, Demucs, Whisper, MusicGen.
- [ ] Add `dev/yaak` workspace for developer testing.
- [ ] Decide queue (Redis/RabbitMQ) and storage (S3/MinIO) provider.

Phase B — Prototype
- [ ] Implement Demucs prototype service (fastapi) and orchestrator adapter (we already scaffolded these).
- [ ] Validate local flow with `docker-compose.micro.yml`.
- [ ] Update frontend to call orchestrator endpoints (simple swap if old endpoints exist).

Phase C — Queue & real model
- [ ] Integrate queue for job submission (e.g., Redis).
- [ ] Add real GPU worker with pinned Torch version for Demucs.
- [ ] Validate outputs & metadata on staging.

Phase D — Repeat for other models
- [ ] Implement Whisper, MusicGen, PitchAnalysis, Gemma3N following the same pattern.

Phase E — Hardening & production
- [ ] Add monitoring, tracing, and CI.
- [ ] Deploy to staging & run e2e tests.
- [ ] Roll out to production with canary.

Validation after each Phase:
- Successful job end-to-end.
- Security tests (unauthenticated requests blocked).
- Logging/tracing correlation works.

## 28 — Final notes & recommended priorities
- Priority order for implementation
  1. Orchestrator + Demucs prototype (done as scaffold).
  2. Queue integration + real GPU worker for Demucs.
  3. Whisper & other model services.
  4. CI & monitoring.
  5. Production rollout.

- Keep model dependency pinning strictly per-service. This avoids Python extension & GPU compatibility conflicts (the original cause of `blis` builds).
- Use pre-signed URLs and S3 to avoid huge data transfers through orchestrator.
- Start with CPU-only tests and then transition to GPU images in staging.

---

If you want I can also:
- Create `dev/openapi/` and `dev/yaak/` artifacts for the Demucs prototype.
- Add `dev/README.micro.md` with the exact `docker compose` commands and a sample JWT helper script.

Implement these next steps by telling me which artifact you want me to create first.
