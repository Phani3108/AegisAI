# AegisAI — Tasks

**Rules:** Every task lives here. Use `[ ]` open, `[x]` done. Link PRs/commits on the same line when useful.

## Phase 0 — Bootstrap and lab

- [x] Create `planning.md` with roadmap, expansions, integration catalog, design and architecture specs
- [x] Create `tasks.md` (this file) with initial tasks
- [x] Create `LOG.md` and record prompts + completions
- [x] Create minimal `README.md` (quickstart: clone, Ollama, run smoke test — stub ok until app exists)
- [x] Scaffold repo layout (`src/`, `benchmarks/`, `docs/adr/`)
- [x] Automated E2E tests (`tests/test_e2e_deep.py`, `scripts/verify_e2e.sh`) — real Ollama smoke still optional in LOG

## Phase 0 — Engineering

- [x] Define OpenAPI sketch for `JobRequest` / `JobEvent` (Pydantic schemas + `/v1/jobs` stub)
- [x] Implement first **batch** pipeline: image → vision model → local LLM → response (async jobs + `/v1/ready`)
- [x] Benchmark harness v0: `benchmarks/run_v0.py` (latency + Ollama token hints; memory profiling later)
- [x] `video_ref` pipeline: ffmpeg keyframes → per-frame vision → LLM (`video_sampling` on `JobRequest`)

## Phase 1+

- [x] Hybrid router: `config/routing_policy.yaml` + `GET /v1/policy` + policy `JobEvent` + `force_local_only` kill switch
- [x] RAG: **minimal** path — `document_ref` with Ollama embeddings + in-memory cosine top-k (no vector DB yet)
- [x] Persistent vector DB + ingest API (**Chroma** + `/v1/collections/*` + `rag_collection` jobs)
- [x] Observability: Prometheus-style counters + rolling latency (`/v1/metrics`, `GET /metrics`)
- [x] Observability (minimal): `X-Request-ID` + job_create INFO logs + **optional OTEL** (`aegisai[otel]`, `AEGISAI_OTEL_ENABLED`)
- [x] Real-time: **SSE** `POST /v1/stream/chat` (Ollama streaming proxy)
- [x] Fine-tuning track: [`experiments/train_lora.py`](experiments/train_lora.py) stub + CI gate ([`docs/fine_tune/PLAYBOOK.md`](docs/fine_tune/PLAYBOOK.md))

## Phase 2 — Platform hardening (T1-lite)

- [x] Optional **`AEGISAI_API_KEY`** middleware for `/v1/*` (Bearer + `X-API-Key`)
- [x] Concurrent job cap (`AEGISAI_MAX_CONCURRENT_JOBS`) + 429 + `jobs_in_flight` metric
- [x] **`Idempotency-Key`** on `POST /v1/jobs` (in-memory dedupe)
- [x] Benchmark harness in-package [`aegisai.benchmarks.image_v0`](src/aegisai/benchmarks/image_v0.py) + CI test

## Phase 3 — Real-time / bounded APIs (planning §4.1, §6)

- [x] **`POST /v1/query`** — sync bounded chat (`AEGISAI_QUERY_TIMEOUT_S`)
- [x] **`GET /v1/jobs/{id}/events`** — SSE job event stream until terminal status
- [x] **`output_schema`** on jobs → Ollama JSON mode + `result.structured.parsed` ([`job_runner`](src/aegisai/services/job_runner.py))

## Phase 4 — Cancellation, WebSocket, QA gate

- [x] **`POST /v1/jobs/{id}/cancel`** + cooperative worker checks ([`job_cancel`](src/aegisai/services/job_cancel.py), [`job_runner`](src/aegisai/services/job_runner.py))
- [x] **WebSocket** `/v1/ws/jobs/{id}` ([`v1_jobs`](src/aegisai/api/routes/v1_jobs.py))
- [x] Prometheus **`jobs_cancelled_total`** + per-pipeline cancelled series
- [x] **`scripts/qa_verify.sh`** + CI runs full QA (ruff, pytest -v, ci_gate, compileall, build)

## Phase 5 — Packaging & discoverability

- [x] **Dockerfile** + [.dockerignore](.dockerignore) (ffmpeg, Chroma volume, policy path)
- [x] **docker-compose.yml** — `aegisai` + `ollama` with named volumes
- [x] **`GET /version`** — package version; exempt from optional API key (with `/health`)
- [x] **README** — full TOC, API table, env table, Docker + QA ([README.md](README.md))

## Phase 6 — Operations polish

- [x] **`AEGISAI_LOG_JSON`** — newline-delimited JSON logs ([`logging_json.py`](src/aegisai/logging_json.py))
- [x] **WebSocket shared-secret** — Bearer / `X-API-Key` / `?api_key=` ([`ws_auth.py`](src/aegisai/middleware/ws_auth.py), [`v1_jobs`](src/aegisai/api/routes/v1_jobs.py))
- [x] **CI `docker-build` job** — verify image build ([`.github/workflows/ci.yml`](.github/workflows/ci.yml))
- [x] Tests [`tests/test_phase6_ws_auth.py`](tests/test_phase6_ws_auth.py)

## Phase 7 — Kubernetes probes

- [x] **`GET /live`** — liveness ([`health.py`](src/aegisai/api/routes/health.py))
- [x] **`GET /ready`** — Ollama + Chroma persist writable ([`readiness.py`](src/aegisai/services/readiness.py)); exempt from API key
- [x] **`GET /v1/ready`** — same checks behind optional API key
- [x] Helm **`livenessProbe` → `/live`**, **`readinessProbe` → `/ready`** ([`deploy/helm/aegisai`](deploy/helm/aegisai/templates/deployment.yaml))
- [x] Tests [`tests/test_phase7_probes.py`](tests/test_phase7_probes.py)

## Phase 8 — Request throttling (T1-lite)

- [x] **`AEGISAI_RATE_LIMIT_PER_MINUTE`** — rolling 60s / client IP / **`/v1/*`** ([`rate_limit.py`](src/aegisai/middleware/rate_limit.py))
- [x] Counter **`http_429_rate_limited_total`** + Prometheus ([`metrics.py`](src/aegisai/services/metrics.py))
- [x] Middleware order: rate limit outer → API key → request ID ([`main.py`](src/aegisai/main.py))
- [x] Tests [`tests/test_phase8_rate_limit.py`](tests/test_phase8_rate_limit.py)

## Phase 9 — Integrator UX & Redis (plan refresh)

- [x] **[planning.md](planning.md) §9** — Chroma + hybrid scope + open items clarified
- [x] **OpenAPI** — tag blurbs, summaries, `common_error_responses`, request **examples** on [`JobRequest`](src/aegisai/schemas/jobs.py) / [`StreamChatRequest`](src/aegisai/schemas/stream.py); [`openapi_extra.py`](src/aegisai/api/openapi_extra.py)
- [x] **Integrator kit** — [`examples/http/smoke.http`](examples/http/smoke.http), [`docs/integrators/SDK.md`](docs/integrators/SDK.md)
- [x] **Demo UI** — [`examples/demo-ui/`](examples/demo-ui/) (static `index.html` + README)
- [x] **Redis optional** — [`AEGISAI_REDIS_URL`](src/aegisai/config.py), [`redis_util`](src/aegisai/services/redis_util.py), [`job_store`](src/aegisai/services/job_store.py) idempotency + [`rate_limit`](src/aegisai/middleware/rate_limit.py); extra **`aegisai[redis]`**; tests [`tests/test_redis_backends.py`](tests/test_redis_backends.py)

## Phase 10 — Frontend polish (demo UI)

- [x] White background + improved visual hierarchy ([`examples/demo-ui/index.html`](examples/demo-ui/index.html))
- [x] Better controls: readiness check, beautify JSON, copy/clear response, auto-refresh polling
- [x] UI docs refreshed ([`examples/demo-ui/README.md`](examples/demo-ui/README.md), [`README.md`](README.md))

## Phase 11 — Frontend realtime controls (demo UI)

- [x] Job cancel button for `POST /v1/jobs/{id}/cancel` in the demo UI
- [x] Live SSE event stream panel for `GET /v1/jobs/{id}/events`
- [x] README + demo-ui docs updated for realtime controls

## Phase 12 — Visual onboarding docs

- [x] Captured demo screenshots under [`docs/images/screenshots/`](docs/images/screenshots/)
- [x] Added simple README screenshot carousel section
- [x] Kept README wording short and easy to read

## Phase 13 — Durable job backbone

- [x] Persisted jobs + job requests to disk-backed state in [`job_store`](src/aegisai/services/job_store.py)
- [x] Added startup recovery for queued/running jobs ([`job_recovery.py`](src/aegisai/services/job_recovery.py), wired in [`main.py`](src/aegisai/main.py))
- [x] Kept existing API contract stable while adding durable behavior ([`v1_jobs`](src/aegisai/api/routes/v1_jobs.py))

## Phase 14 — Distributed control semantics

- [x] Idempotency request fingerprint with conflict protection for key reuse ([`v1_jobs`](src/aegisai/api/routes/v1_jobs.py), [`job_store`](src/aegisai/services/job_store.py))
- [x] Distributed cancellation path using Redis when configured ([`job_cancel`](src/aegisai/services/job_cancel.py))
- [x] Retry/dead-letter counters and transient retry wrapper in job guard ([`v1_jobs`](src/aegisai/api/routes/v1_jobs.py), [`metrics`](src/aegisai/services/metrics.py), [`config`](src/aegisai/config.py))

## Phase 15 — Resilience + observability upgrades

- [x] Ollama retry/backoff settings and client wrappers ([`config`](src/aegisai/config.py), [`ollama/client.py`](src/aegisai/ollama/client.py))
- [x] Retry settings propagated to query/stream/collections/readiness and pipeline runner
- [x] Added latency p95/p99 plus retry/dead-letter metrics in Prometheus ([`metrics`](src/aegisai/services/metrics.py))
- [x] Request-id context propagation in JSON logs ([`request_id` middleware](src/aegisai/middleware/request_id.py), [`logging_json`](src/aegisai/logging_json.py))

## Phase 16 — Security + governance baseline

- [x] Added `auth_mode` (`api_key`/`jwt`/`both`) with HS256 Bearer JWT path in middleware
- [x] Added optional secure ops endpoint protection (`/ready`, `/metrics`) via config
- [x] Added role-aware hybrid routing policy support (`hybrid_allowed_roles`) and tests

## Phase 17 — Operator UX + frontend reliability

- [x] Added auth header mode selector (Bearer / X-API-Key) to demo UI
- [x] Replaced EventSource with header-capable fetch SSE stream parser for authenticated streaming
- [x] Added structured payload builder templates (image/document/video) to reduce JSON mistakes
- [x] **Lab UI v2:** Google Labs–inspired layout, desert-sand theme, populated policy/mode/poll/video/RAG dropdowns, collections loader, idempotency field, health/version/metrics shortcuts ([`examples/demo-ui/index.html`](examples/demo-ui/index.html))

## Phase 18 — Scale validation + release hardening

- [x] Added production Helm defaults (resources/security contexts/persistence/HPA/PDB)
- [x] Added scale/failover validation runbook (`docs/operations/scale_validation.md`)
- [x] Added release hardening checklist (`docs/operations/release_checklist.md`) and known limits section in README

## Phase 19 — Inference abstraction (scale path)

- [x] `InferenceBackend` protocol + `create_inference_backend` factory ([`src/aegisai/inference/`](src/aegisai/inference/)); Ollama as default adapter
- [x] `app.state.inference` (job/stream/embed timeout) + `app.state.inference_query` (bounded `POST /v1/query`); pipelines + job runner + recovery + readiness use injected backend
- [x] `AEGISAI_INFERENCE_BACKEND` in settings / `.env.example` (today: `ollama` only)

---

## Backlog / ideas (not committed)

- [ ] **Strategy:** [docs/strategy/expansion_roadmap.md](docs/strategy/expansion_roadmap.md) — industries, S/M/L use cases, personas, integration map; **next shipped phases: P20+** (second inference backend = P24 per roadmap)
- [x] Scene detection for smarter video keyframes (`video_sampling.scene_detection` + ffmpeg)
- [x] DLP integration prototype for hybrid mode ([`src/aegisai/dlp/scan.py`](src/aegisai/dlp/scan.py))
- [x] K8s Helm chart (T2) — [`deploy/helm/aegisai`](deploy/helm/aegisai)
