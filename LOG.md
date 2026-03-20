# AegisAI — Prompt & completion log

Append-only chronological record. Each entry: **date**, **user prompt (summary)**, **actions completed**, **files touched**, **notes**.

---

## 2026-03-20

### Entry 1 — Initial vision (session start)

- **Prompt summary:** Local multimodal enterprise privacy stack; modules (Ollama, vision, RAG, benchmarks, hybrid router, observability); gaps: monitoring, real-time, fine-tuning; require `tasks.md` + `planning.md` and strict recording of prompts/tasks.
- **Actions:** Cursor plan drafted (bootstrap + roadmap). Files in repo not yet created in that turn.
- **Files:** (plan artifact only at plan time)

### Entry 2 — Continue

- **Prompt summary:** “Continue” — proceed with prior bootstrap plan.
- **Actions:** Plan file finalized in Cursor plans: `aegisai_project_bootstrap_5a35e951.plan.md` (bootstrap docs + conventions + phases).
- **Files:** `.cursor/plans/...` (Cursor-managed)

### Entry 3 — Deepen plan

- **Prompt summary:** Go deeper on expansions, integrations, design specs, architecture specs.
- **Actions:** Expanded strategic planning: maturity tiers T0–T5, full integration catalog (serving, vision, ASR, vector, enterprise, real-time, MLOps), API/policy/UX design specs, NFRs, threat model stub, deployment topologies, observability + benchmark specs, ADR process, phased real-time and fine-tuning paths.
- **Files created/updated:** `planning.md`, `tasks.md`, `LOG.md` (this entry)

### Entry 4 — FastAPI preference

- **Prompt summary:** Prefer Python FastAPI; add the documents (scaffold + docs).
- **Actions:** Added `pyproject.toml` (hatchling, FastAPI, Uvicorn, httpx, pydantic), `src/aegisai/` app with `/health`, `/v1/jobs` POST+GET stub, Pydantic schemas (`JobRequest`, `JobEvent`, etc.), `README.md` quickstart, `docs/adr/0000-template.md`, `docs/adr/0001-python-fastapi-control-plane.md`, `benchmarks/README.md`, `.gitignore`. Updated `planning.md` §9 and stack pointer. Verified editable install and import.
- **Files:** `pyproject.toml`, `.gitignore`, `README.md`, `src/aegisai/**`, `docs/adr/*`, `benchmarks/README.md`, `planning.md`, `tasks.md`, `LOG.md`

### Entry 5 — Build Phase 0 pipeline

- **Prompt summary:** Proceed with building the project.
- **Actions:** Ollama async client, pydantic-settings config, two-step image pipeline (vision model then text LLM), `file://` resolution with optional `AEGISAI_MEDIA_ROOT`, async job runner + in-memory store + BackgroundTasks, `GET /v1/ready`, hybrid rejected for confidential/regulated labels, `SamplingPolicy` + ffmpeg keyframe prototype (`pipelines/video.py`; `video_ref` jobs not wired), `benchmarks/run_v0.py`, `.env.example`, pytest suite (MockTransport + API test). Ruff + pytest pass. Ollama was not running on the verification host; user should run `/v1/ready` and a real image job locally and append hardware notes to this log.
- **Files:** `pyproject.toml`, `src/aegisai/main.py`, `src/aegisai/config.py`, `src/aegisai/ollama/*`, `src/aegisai/pipelines/*`, `src/aegisai/schemas/video.py`, `src/aegisai/services/*`, `src/aegisai/api/routes/v1_jobs.py`, `benchmarks/run_v0.py`, `benchmarks/README.md`, `.env.example`, `tests/*`, `README.md`, `tasks.md`, `LOG.md`

### Entry 6 — Video + RAG

- **Prompt summary:** Continue building the project.
- **Actions:** Refactored shared vision/LLM helpers (`pipelines/vision_steps.py`); image pipeline records `ingest_ms`. Implemented **`video_ref`** end-to-end: `JobRequest.video_sampling` (`SamplingPolicy`), `video_job.py` (temp frames dir, per-frame VLM, LLM summary), `extract_keyframes` now writes into a caller-provided directory. Implemented **`document_ref`** minimal RAG (`rag.py`): chunking, Ollama `/api/embeddings`, cosine top-k, LLM over excerpts; `OllamaClient.embed`; settings `embed_model`, `rag_*`. Job runner enforces **one media type per job**; latency includes `ingest_ms` / `retrieval_ms` as applicable; structured results include `frame_count` / `chunk_count`. Tests: RAG httpx mock, video pipeline with patched `extract_keyframes`, API media-conflict failure. Docs: README, `.env.example`, `tasks.md`.
- **Files:** `src/aegisai/pipelines/vision_steps.py`, `src/aegisai/pipelines/image.py`, `src/aegisai/pipelines/video.py`, `src/aegisai/pipelines/video_job.py`, `src/aegisai/pipelines/rag.py`, `src/aegisai/schemas/jobs.py`, `src/aegisai/config.py`, `src/aegisai/ollama/client.py`, `src/aegisai/services/job_runner.py`, `tests/test_rag_pipeline.py`, `tests/test_video_job.py`, `tests/test_jobs_api.py`, `README.md`, `.env.example`, `tasks.md`, `LOG.md`

### Entry 7 — Routing policy + request IDs

- **Prompt summary:** Continue.
- **Actions:** YAML routing policy (`config/routing_policy.yaml`, `AEGISAI_ROUTING_POLICY_PATH`), `RoutingPolicy` + `load_routing_policy`, `pyyaml` dependency, `app.state.policy`, `GET /v1/policy`, hybrid eligibility enforced from file + `force_local_only`, first `JobEvent` is `policy`, `RequestIdMiddleware` + `X-Request-ID`, INFO `job_create` logging, tests in `tests/test_policy_routes.py`.
- **Files:** `pyproject.toml`, `config/routing_policy.yaml`, `src/aegisai/policy/*`, `src/aegisai/middleware/*`, `src/aegisai/config.py`, `src/aegisai/main.py`, `src/aegisai/api/routes/v1_jobs.py`, `tests/test_policy_routes.py`, `.env.example`, `README.md`, `tasks.md`, `LOG.md`

### Entry 8 — Chroma, SSE, OTEL stub, fine-tune playbook

- **Prompt summary:** Continue with next phases.
- **Actions:** Added **chromadb** dependency, `AEGISAI_CHROMA_PERSIST_DIR`, PersistentClient in lifespan, `rag_store/` (sanitize names for Chroma 3+ char rules), `upsert_documents` chunk+embed+add, `/v1/collections` CRUD-ish API, `JobRequest.rag_collection` + validation, `run_chroma_rag_pipeline`, job_runner branch + `store: chroma|ephemeral`. **SSE** `POST /v1/stream/chat` via `OllamaClient.chat_stream`. Optional **OTEL** `aegisai[otel]` + `maybe_instrument`. **`docs/fine_tune/PLAYBOOK.md`**. Tests `tests/test_chroma_api.py`. Pydantic `JobRequest` validator fix (field_validator strip). `.gitignore` `data/chroma/`.
- **Files:** `pyproject.toml`, `.gitignore`, `src/aegisai/config.py`, `src/aegisai/main.py`, `src/aegisai/ollama/client.py`, `src/aegisai/schemas/jobs.py`, `src/aegisai/schemas/collections.py`, `src/aegisai/schemas/stream.py`, `src/aegisai/rag_store/*`, `src/aegisai/pipelines/rag_chroma.py`, `src/aegisai/api/routes/v1_collections.py`, `src/aegisai/api/routes/v1_stream.py`, `src/aegisai/telemetry/otel.py`, `src/aegisai/services/job_runner.py`, `src/aegisai/api/routes/v1_jobs.py`, `tests/test_chroma_api.py`, `docs/fine_tune/PLAYBOOK.md`, `.env.example`, `README.md`, `tasks.md`, `LOG.md`

### Entry 9 — E2E verification + GitHub push

- **Prompt summary:** End-to-end deep testing; push to GitHub `Phani3108/AegisAI`.
- **Actions:** Added `tests/test_e2e_deep.py` (Chroma+RAG job flow + mocked image job), `scripts/verify_e2e.sh`, dev deps `pytest-cov`, `build`; ran **ruff**, **compileall**, **15 pytest** tests, **`python -m build`** (sdist+wheel OK). Added **MIT** `LICENSE`, README repo link + verify script section. Initialized git in project dir, `main` branch, pushed to `origin` (https://github.com/Phani3108/AegisAI).
- **Files:** `tests/test_e2e_deep.py`, `scripts/verify_e2e.sh`, `pyproject.toml`, `LICENSE`, `README.md`, `tasks.md`, `LOG.md`

### Entry 20 — README: CI badge, status line, install extras, readiness smoke fix

- **Actions:** GitHub Actions **CI badge**; **Phases 0–9** + extras summary; Phase 8/9 table wording; **`pip install -e ".[dev,otel]"`** / **`redis`** hints; smoke checks use **`GET /ready`** (document **`/v1/ready`** + API key).

### Entry 21 — Phase 10: frontend demo polish (white UI + richer controls)

- **Prompt summary:** Continue to next phase, ensure frontend has white background and improved elements, run thorough QA, then push.
- **Actions:** Rebuilt [`examples/demo-ui/index.html`](examples/demo-ui/index.html) with white background card layout, improved typography/buttons, readiness status pill, policy/readiness actions, sample+beautify JSON, create/refresh job flow, auto-refresh polling (2s/5s/10s), and response copy/clear with timestamps. Updated frontend docs and roadmap (`README`, `tasks`, `planning`).

### Entry 22 — Phase 11: realtime frontend controls (cancel + SSE events)

- **Prompt summary:** Continue next frontend phase with thorough testing and push.
- **Actions:** Extended [`examples/demo-ui/index.html`](examples/demo-ui/index.html) with **Cancel Job** action (`POST /v1/jobs/{id}/cancel`) and a live **SSE events panel** for `/v1/jobs/{id}/events` (start/stop stream controls + event log). Updated [`examples/demo-ui/README.md`](examples/demo-ui/README.md), [`README.md`](README.md), [`tasks.md`](tasks.md), and [`planning.md`](planning.md) for Phase 11.

### Entry 23 — Phase 12: screenshots + README carousel

- **Prompt summary:** Take project screenshots, add them to README in carousel mode, keep language simple, push to GitHub.
- **Actions:** Captured screenshots to [`docs/images/screenshots/`](docs/images/screenshots/) using Playwright CLI from the live demo page: `demo-home.png`, `demo-sample.png`, `demo-polling.png`. Added a simple collapsible carousel section to [`README.md`](README.md), kept wording minimal, and updated [`tasks.md`](tasks.md).

### Entry 24 — Phase 13: durable jobs + restart recovery

- **Prompt summary:** Implement forward plan phase for durable job backbone.
- **Actions:** Added disk-backed persistence for jobs/requests/idempotency in [`job_store`](src/aegisai/services/job_store.py) and startup recovery task in [`job_recovery.py`](src/aegisai/services/job_recovery.py), wired through [`main.py`](src/aegisai/main.py). Kept API endpoints stable in [`v1_jobs`](src/aegisai/api/routes/v1_jobs.py). Full QA gate passed (52 tests).

### Entry 25 — Phase 14: distributed controls (idempotency hash, cancel path, retry counters)

- **Prompt summary:** Continue forward plan with distributed idempotency/cancel semantics and retry/dead-letter behavior.
- **Actions:** Added request-payload hash protection for idempotency key reuse (`409` on mismatch) in [`v1_jobs`](src/aegisai/api/routes/v1_jobs.py) + [`job_store`](src/aegisai/services/job_store.py), added Redis-backed distributed cancellation in [`job_cancel`](src/aegisai/services/job_cancel.py), added transient retry wrapper + dead-letter marking and new counters in [`metrics`](src/aegisai/services/metrics.py), with configurable retry attempts in [`config`](src/aegisai/config.py). Full QA gate passed (52 tests).

### Entry 26 — Phase 15: resilience + observability uplift

- **Prompt summary:** Continue forward plan phase for transient retries and better observability.
- **Actions:** Added Ollama retry/backoff settings and wrappers in [`ollama/client.py`](src/aegisai/ollama/client.py) + [`config`](src/aegisai/config.py), wired retry options into query/stream/collections/readiness/pipeline callers, added p95/p99 latency metrics plus retry/dead-letter counters in [`metrics`](src/aegisai/services/metrics.py), and added request-id context propagation for JSON logs via [`request_context`](src/aegisai/services/request_context.py), [`request_id` middleware](src/aegisai/middleware/request_id.py), and [`logging_json`](src/aegisai/logging_json.py). Full QA gate passed (52 tests).

### Entry 27 — Phase 16: security + governance baseline

- **Prompt summary:** Add OIDC/JWT-capable auth path, role checks, and endpoint protection model.
- **Actions:** Extended middleware to support `api_key` / `jwt` / `both` modes with HS256 Bearer token verification and role extraction in [`api_key`](src/aegisai/middleware/api_key.py); added optional protected ops endpoints (`/ready`, `/metrics`) via config; extended routing policy with `hybrid_allowed_roles` and applied role-aware hybrid checks in job creation flow. Added security tests in [`tests/test_phase16_security.py`](tests/test_phase16_security.py). Full QA gate passed (54 tests).

### Entry 28 — Phase 17: operator UX + frontend reliability

- **Prompt summary:** Upgrade frontend for auth-capable streaming and cleaner structured input flow.
- **Actions:** Updated demo UI with auth header mode selector (Bearer or X-API-Key), replaced EventSource-based SSE with a header-capable fetch stream parser, and added structured payload templates for image/document/video in [`examples/demo-ui/index.html`](examples/demo-ui/index.html). Updated demo docs in [`examples/demo-ui/README.md`](examples/demo-ui/README.md). Full QA gate passed (54 tests).

### Entry 29 — Phase 18: scale validation + release hardening

- **Prompt summary:** Finalize scale/release readiness with production deployment defaults and validation docs.
- **Actions:** Updated Helm values/deployment defaults for production (resources, security contexts, persistence, HPA, PDB) and added HPA/PDB templates under [`deploy/helm/aegisai/templates`](deploy/helm/aegisai/templates). Added operations docs: [`scale_validation.md`](docs/operations/scale_validation.md) and [`release_checklist.md`](docs/operations/release_checklist.md), plus README operations/known-limits links. Full QA gate passed (54 tests).

### Entry 19 — Phase 9: OpenAPI polish, integrator kit, demo UI, optional Redis

- **Prompt summary:** Implement attached plan (planning §9, OpenAPI, .http + SDK doc, demo UI, Redis idempotency/rate limit).
- **Actions:** [`openapi_extra.py`](src/aegisai/api/openapi_extra.py); route summaries/responses; schema examples; [`examples/http/smoke.http`](examples/http/smoke.http); [`docs/integrators/SDK.md`](docs/integrators/SDK.md); [`examples/demo-ui/`](examples/demo-ui/); **`AEGISAI_REDIS_URL`** + **`AEGISAI_IDEMPOTENCY_TTL_SECONDS`**; [`redis_util`](src/aegisai/services/redis_util.py); Redis paths in job_store + rate_limit; **`pyproject.toml`** extras **`redis`** + dev **`fakeredis`**; [`tests/test_redis_backends.py`](tests/test_redis_backends.py); README/tasks/planning; `.env.example`. **`qa_verify.sh`:** 52 passed.

### Entry 18 — Phase 8: /v1 rate limit + metric

- **Actions:** **`AEGISAI_RATE_LIMIT_PER_MINUTE`**; **`RateLimitMiddleware`** (per-IP deque, 60s window); **`record_rate_limited`** + Prometheus; **`reset_for_tests`** in conftest; [`tests/test_phase8_rate_limit.py`](tests/test_phase8_rate_limit.py); README/tasks. **`qa_verify.sh`:** 49 passed.

### Entry 17 — Phase 7: Kubernetes /live, /ready, Helm probes

- **Prompt summary:** Next phases; deep QA per phase; push to GitHub.
- **Actions:** Shared [`readiness_details`](src/aegisai/services/readiness.py) (Ollama `/api/tags` + Chroma dir write probe); **`GET /live`**, **`GET /ready`** (API-key exempt); refactor **`GET /v1/ready`**; Helm **`livenessProbe` / `readinessProbe`** paths; [`tests/test_phase7_probes.py`](tests/test_phase7_probes.py); README/tasks. **`qa_verify.sh`:** 46 passed.

### Entry 16 — Phase 6: JSON logging, WebSocket API key, CI docker-build

- **Prompt summary:** Continue next phases; QA and push.
- **Actions:** **`AEGISAI_LOG_JSON`** + `configure_logging` / `JsonLogFormatter`; **`websocket_shared_secret_authorized`** before WS accept (4401 on mismatch); **`.github/workflows/ci.yml`** `docker-build` job (`docker build`); **tests/test_phase6_ws_auth.py**; README + `.env.example` + tasks/planning. **`qa_verify.sh`:** 41 passed.
- **Files:** `src/aegisai/logging_json.py`, `src/aegisai/config.py`, `src/aegisai/main.py`, `src/aegisai/middleware/ws_auth.py`, `src/aegisai/api/routes/v1_jobs.py`, `.github/workflows/ci.yml`, `.env.example`, `tests/test_phase6_ws_auth.py`, `README.md`, `tasks.md`, `LOG.md`, `planning.md`

### Entry 15 — Phase 5: Docker, Compose, /version, README overhaul

- **Prompt summary:** Next phase + thorough QA + push; README updated properly.
- **Actions:** **Dockerfile** (Python 3.12-slim, ffmpeg, pip install, `AEGISAI_*` defaults for chroma + policy path); **docker-compose.yml** (Ollama + AegisAI, volumes); **.dockerignore**; **`GET /version`** in [`health`](src/aegisai/api/routes/health.py); **API key** middleware exempts `/version`; **test_version_endpoint.py**. **README** rewritten: TOC, phase table, Docker quickstarts, consolidated API + env tables, security/observability/dev sections. **QA:** `qa_verify.sh` — **38 passed**; `docker build` not run (daemon unavailable on host). **tasks.md** Phase 5.
- **Files:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `src/aegisai/api/routes/health.py`, `src/aegisai/middleware/api_key.py`, `tests/test_version_endpoint.py`, `README.md`, `tasks.md`, `LOG.md`, `planning.md`

### Entry 14 — Phase 4: cancel, WebSocket events, metrics, QA script

- **Prompt summary:** Next phases with thorough QA after completion and push to GitHub.
- **Actions:** **`job_cancel`** cooperative cancellation; **`POST /v1/jobs/{id}/cancel`**; worker checkpoints + exception path honors cancel; **`GET /v1/ws/jobs/{id}`** WebSocket event stream; **`jobs_cancelled_total`** + Prometheus by-pipeline cancelled; **`scripts/qa_verify.sh`** (ruff, pytest -v --durations, ci_gate, compileall, build); **`.github/workflows/ci.yml`** runs QA script; tests [`tests/test_phase4_cancel_ws.py`](tests/test_phase4_cancel_ws.py); conftest resets cancel flags. Ran full **`qa_verify.sh`** locally (37 passed).
- **Files:** `src/aegisai/services/job_cancel.py`, `src/aegisai/services/job_runner.py`, `src/aegisai/services/metrics.py`, `src/aegisai/api/routes/v1_jobs.py`, `tests/conftest.py`, `tests/test_metrics_api.py`, `tests/test_phase4_cancel_ws.py`, `scripts/qa_verify.sh`, `.github/workflows/ci.yml`, `README.md`, `tasks.md`, `LOG.md`

### Entry 13 — Phase 3: /v1/query, job SSE, output_schema JSON

- **Prompt summary:** Next phases — real-time / bounded APIs per planning.
- **Actions:** **`POST /v1/query`** with `query_timeout_s`; **`GET /v1/jobs/{id}/events`** SSE (poll); **`OllamaClient.chat(response_format=...)`**; **`llm_answer_from_evidence`** + all pipelines pass `output_schema`; **`_structured_with_optional_json`** on job results; tests [`tests/test_phase3.py`](tests/test_phase3.py). Docs: README, `.env.example`, `tasks.md`.
- **Files:** `src/aegisai/config.py`, `src/aegisai/ollama/client.py`, `src/aegisai/pipelines/vision_steps.py`, `src/aegisai/pipelines/image.py`, `src/aegisai/pipelines/video_job.py`, `src/aegisai/pipelines/rag.py`, `src/aegisai/pipelines/rag_chroma.py`, `src/aegisai/services/job_runner.py`, `src/aegisai/api/routes/v1_query.py`, `src/aegisai/api/routes/v1_jobs.py`, `src/aegisai/main.py`, `tests/test_phase3.py`, `README.md`, `.env.example`, `tasks.md`, `LOG.md`

### Entry 12 — Backlog: scene keyframes, DLP hybrid, audit NDJSON, Helm

- **Prompt summary:** Continue with the rest of backlog changes.
- **Actions:** **`video_sampling.scene_detection`** + `scene_threshold` using ffmpeg `select=gt(scene,…)`; **`aegisai.dlp.scan`** + `AEGISAI_DLP_*` + 400 on hybrid when patterns in text; **`GET /v1/jobs/{id}/audit`** JSON + `?format=ndjson`; **Helm** under `deploy/helm/aegisai` (Deployment, Service, optional PVC). Tests: `test_dlp_*`, `test_*audit*`, `test_video_scene_ffmpeg`. README / `.env.example` / `tasks.md`.
- **Files:** `src/aegisai/schemas/video.py`, `src/aegisai/pipelines/video.py`, `src/aegisai/dlp/*`, `src/aegisai/api/routes/v1_jobs.py`, `deploy/helm/aegisai/**`, `tests/test_dlp_scan.py`, `tests/test_dlp_api.py`, `tests/test_audit_route.py`, `tests/test_video_scene_ffmpeg.py`, `README.md`, `.env.example`, `tasks.md`, `LOG.md`

### Entry 11 — Phase 2 platform (auth cap, idempotency, benchmark module)

- **Prompt summary:** Continue next phases — Phase 2 hardening per planning.md.
- **Actions:** **`APIKeyMiddleware`** (`AEGISAI_API_KEY`) for `/v1/*`; **`JobConcurrencyLimiter`** + 429 on overload; **`_execute_job_guarded`** releases slot in `finally`; **idempotency** map in `job_store` + `Idempotency-Key`; metrics **`jobs_in_flight`**; **`aegisai.benchmarks.image_v0.run_image_benchmark`** with thin `benchmarks/run_v0.py` CLI; tests `test_phase2_platform.py`, `test_benchmark_image_v0.py`; **conftest** resets jobs + limiter; README / `.env.example` / `tasks.md`.
- **Files:** `src/aegisai/config.py`, `src/aegisai/main.py`, `src/aegisai/middleware/api_key.py`, `src/aegisai/services/job_concurrency.py`, `src/aegisai/services/job_store.py`, `src/aegisai/services/metrics.py`, `src/aegisai/api/routes/v1_jobs.py`, `src/aegisai/benchmarks/*`, `benchmarks/run_v0.py`, `benchmarks/README.md`, `tests/conftest.py`, `tests/test_phase2_platform.py`, `tests/test_benchmark_image_v0.py`, `README.md`, `.env.example`, `tasks.md`, `LOG.md`

### Entry 10 — Metrics, CI gate, train stub

- **Prompt summary:** Continue next phases: observability/metrics, CI, benchmark gate, runnable fine-tuning stub.
- **Actions:** Fixed FastAPI `GET /v1/metrics` with `response_model=None` (union JSON/Prometheus). In-process metrics (`jobs_completed_total`, `jobs_failed_total`, per-pipeline, rolling latency), `GET /metrics` scrape, `job_runner` recording, `tests/test_metrics_api.py` + `conftest` reset. **`.github/workflows/ci.yml`**: ruff, pytest, `scripts/ci_gate.py`, build. **`experiments/train_lora.py`**: dry-run default, `--execute` import check. **PLAYBOOK** links to experiments + CI. Ruff line-wrap in `metrics.py`. **tasks.md** Phase 1+ checkboxes updated.
- **Files:** `src/aegisai/api/routes/v1_metrics.py`, `src/aegisai/api/routes/ops_metrics.py`, `src/aegisai/services/metrics.py`, `src/aegisai/services/job_runner.py`, `src/aegisai/main.py`, `tests/conftest.py`, `tests/test_metrics_api.py`, `.github/workflows/ci.yml`, `scripts/ci_gate.py`, `experiments/train_lora.py`, `docs/fine_tune/PLAYBOOK.md`, `tasks.md`, `LOG.md`

---

*End of log (append below).*
