# AegisAI

Local multimodal pipeline (vision → LLM → RAG) with an enterprise privacy posture: **local-first**, optional hybrid routing, benchmarks, and observability. See [`planning.md`](planning.md) for architecture and expansion tiers.

**Repository:** [github.com/Phani3108/AegisAI](https://github.com/Phani3108/AegisAI)

## Stack

- **Python 3.11+**, **FastAPI**, **Uvicorn**, **Pydantic Settings**
- **Ollama** (local LLM + vision models) — required to run real jobs

## Phase 0 pipelines

### `image_ref`

1. **Vision model** (`AEGISAI_VISION_MODEL`, default `llava`) describes the image.
2. **Text LLM** (`AEGISAI_LLM_MODEL`, default `llama3.2`) answers using only that description.

Optional `text` inputs supply the user question; otherwise a default summary prompt is used.

### `video_ref`

1. **ffmpeg** samples keyframe PNGs (see `video_sampling` on `JobRequest`: `max_frames`, optional `fps`).
2. **Vision model** describes each sampled frame.
3. **Text LLM** answers from the concatenated frame descriptions.

Requires `ffmpeg` on `PATH`.

### `document_ref` (minimal RAG)

1. Plain text is read from the file (UTF-8, replace errors).
2. **Embeddings** via Ollama `AEGISAI_EMBED_MODEL` (default `nomic-embed-text`).
3. **Cosine top-k** chunks + **LLM** answers from excerpts only.

Only one of `image_ref`, `video_ref`, or `document_ref` per job.

### `rag_collection` (persistent Chroma RAG)

1. **Create** a collection: `POST /v1/collections` with `{ "name": "my_kb" }` (Chroma requires **≥ 3** characters; names are sanitized).
2. **Ingest** chunked documents: `POST /v1/collections/{name}/documents` with `{ "documents": [{ "id": "...", "text": "..." }] }` — embeddings come from Ollama (`AEGISAI_EMBED_MODEL`).
3. **Query** via job: `POST /v1/jobs` with `"rag_collection": "my_kb"` and a non-empty `text` input (the question). No `image_ref` / `video_ref` / `document_ref` on the same job.

Ephemeral file RAG (`document_ref`) is unchanged; job results tag `store: ephemeral` vs `store: chroma`.

### Collections API (summary)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/collections` | List collection names |
| POST | `/v1/collections` | Create (empty) collection |
| POST | `/v1/collections/{name}/documents` | Ingest / upsert chunked docs |
| DELETE | `/v1/collections/{name}` | Drop collection |

Chroma files live under `AEGISAI_CHROMA_PERSIST_DIR` (default `data/chroma`).

### Streaming (SSE)

`POST /v1/stream/chat` accepts `{ "model": "llama3.2", "messages": [{ "role": "user", "content": "Hi" }] }` and returns **Server-Sent Events** streaming Ollama’s NDJSON lines (ends with `data: [DONE]`). Use for real-time UX without waiting for full job completion.

### OpenTelemetry (optional)

```bash
pip install 'aegisai[otel]'
export AEGISAI_OTEL_ENABLED=true
# plus standard OTLP env, e.g. OTEL_EXPORTER_OTLP_ENDPOINT
uvicorn aegisai.main:app --host 127.0.0.1 --port 8000
```

### Fine-tuning (playbook)

See [`docs/fine_tune/PLAYBOOK.md`](docs/fine_tune/PLAYBOOK.md) for dataset, LoRA, and benchmark gate guidance (stub until you add training scripts).

## Routing policy (hybrid)

Hybrid mode (`mode: hybrid`) is gated by [`config/routing_policy.yaml`](config/routing_policy.yaml):

- **`hybrid_allowed_labels`** — sensitivity labels that may use hybrid (default: `public`, `internal`).
- **`force_local_only`** — if `true`, hybrid is always rejected (kill switch).

Inspect the effective rules: `GET /v1/policy`.

Every job stores an initial **`policy`** event with the policy version and route.

## Observability (lightweight)

- Responses include **`X-Request-ID`** (pass the same header to correlate client retries).
- Job creation logs a line at INFO with `job_id`, `request_id`, `mode`, and label.
- Optional **OTEL** FastAPI spans when `AEGISAI_OTEL_ENABLED=true` and `aegisai[otel]` is installed.

## Quickstart

### 1. Ollama

Install [Ollama](https://ollama.com) and pull models (names must match your `.env` if you override defaults):

```bash
ollama pull llama3.2
ollama pull llava
ollama pull nomic-embed-text
ollama list
```

### 2. Python environment

From the repo root:

```bash
cd /path/to/AegisAI
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Copy [`.env.example`](.env.example) to `.env` and adjust if needed.

### 3. Run the API

```bash
uvicorn aegisai.main:app --reload --host 127.0.0.1 --port 8000
```

Open **interactive docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Smoke checks

Health:

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

Ollama connectivity (lists tags when Ollama is up):

```bash
curl -s http://127.0.0.1:8000/v1/ready | python -m json.tool
```

Image job — use an **absolute** `file://` URI to a readable image (when `AEGISAI_MEDIA_ROOT` is set, the file must live under that directory):

```bash
curl -s -X POST http://127.0.0.1:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"inputs":[{"type":"image_ref","uri":"file:///absolute/path/to/image.png"},{"type":"text","text":"What is in this image?"}],"sensitivity_label":"internal","mode":"local_only"}' \
| python -m json.tool
```

Poll until `status` is `succeeded` or `failed`:

```bash
curl -s http://127.0.0.1:8000/v1/jobs/<job_id> | python -m json.tool
```

### 5. Benchmark v0 (CLI)

Requires Ollama running and models pulled:

```bash
python benchmarks/run_v0.py /absolute/path/to/image.png --question "Summarize visible text."
```

### 6. Tests

```bash
pytest -q
```

Deep verification (lint, compile, full suite, optional wheel build):

```bash
./scripts/verify_e2e.sh
```

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `AEGISAI_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama HTTP API |
| `AEGISAI_VISION_MODEL` | `llava` | Vision / VLM |
| `AEGISAI_LLM_MODEL` | `llama3.2` | Text model for second step |
| `AEGISAI_MEDIA_ROOT` | _(unset)_ | If set, `file://` images must resolve under this path |
| `AEGISAI_OLLAMA_TIMEOUT_S` | `600` | Per-request timeout to Ollama |
| `AEGISAI_EMBED_MODEL` | `nomic-embed-text` | Embedding model for `document_ref` |
| `AEGISAI_RAG_CHUNK_SIZE` | `512` | Chunk size (characters) |
| `AEGISAI_RAG_CHUNK_OVERLAP` | `64` | Overlap between chunks |
| `AEGISAI_RAG_TOP_K` | `4` | Chunks passed to the LLM |
| `AEGISAI_ROUTING_POLICY_PATH` | _(auto)_ | YAML file for hybrid rules; default repo `config/routing_policy.yaml` |
| `AEGISAI_CHROMA_PERSIST_DIR` | `data/chroma` | Chroma persistence directory |
| `AEGISAI_OTEL_ENABLED` | `false` | Enable OpenTelemetry instrumentation |

## Repo layout

| Path | Purpose |
|------|---------|
| [`planning.md`](planning.md) | Strategy, integrations, design/architecture specs |
| [`tasks.md`](tasks.md) | Checklist of all work |
| [`LOG.md`](LOG.md) | Prompt and completion audit log |
| `src/aegisai/` | FastAPI app, Ollama client, pipelines, Chroma ingest |
| `docs/fine_tune/` | Fine-tuning playbook (stub) |
| `docs/adr/` | Architecture Decision Records |
| `config/` | Routing policy YAML |
| `benchmarks/` | Harness scripts (datasets later) |
| `tests/` | Pytest suite |

## License

[MIT](LICENSE)
