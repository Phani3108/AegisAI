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

### Entry 10 — Metrics, CI gate, train stub

- **Prompt summary:** Continue next phases: observability/metrics, CI, benchmark gate, runnable fine-tuning stub.
- **Actions:** Fixed FastAPI `GET /v1/metrics` with `response_model=None` (union JSON/Prometheus). In-process metrics (`jobs_completed_total`, `jobs_failed_total`, per-pipeline, rolling latency), `GET /metrics` scrape, `job_runner` recording, `tests/test_metrics_api.py` + `conftest` reset. **`.github/workflows/ci.yml`**: ruff, pytest, `scripts/ci_gate.py`, build. **`experiments/train_lora.py`**: dry-run default, `--execute` import check. **PLAYBOOK** links to experiments + CI. Ruff line-wrap in `metrics.py`. **tasks.md** Phase 1+ checkboxes updated.
- **Files:** `src/aegisai/api/routes/v1_metrics.py`, `src/aegisai/api/routes/ops_metrics.py`, `src/aegisai/services/metrics.py`, `src/aegisai/services/job_runner.py`, `src/aegisai/main.py`, `tests/conftest.py`, `tests/test_metrics_api.py`, `.github/workflows/ci.yml`, `scripts/ci_gate.py`, `experiments/train_lora.py`, `docs/fine_tune/PLAYBOOK.md`, `tasks.md`, `LOG.md`

---

*End of log (append below).*
