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
- [ ] Observability: richer structured logs / metrics beyond JobEvent latencies
- [x] Observability (minimal): `X-Request-ID` + job_create INFO logs + **optional OTEL** (`aegisai[otel]`, `AEGISAI_OTEL_ENABLED`)
- [x] Real-time: **SSE** `POST /v1/stream/chat` (Ollama streaming proxy)
- [ ] Fine-tuning track: executable LoRA/PEFT scripts + CI benchmark gate ([`docs/fine_tune/PLAYBOOK.md`](docs/fine_tune/PLAYBOOK.md) stub)

---

## Backlog / ideas (not committed)

- [ ] Scene detection for smarter video keyframes
- [ ] DLP integration prototype for hybrid mode
- [ ] K8s Helm chart (T2)
