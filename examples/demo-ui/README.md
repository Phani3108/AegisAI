# AegisAI Lab — demo UI (static)

Single-page operator console with a **Google Labs–style** layout: sticky header, section navigation, desert-sand palette, and structured “experiment” controls for the API.

## How to run

1. Start AegisAI (e.g. `docker compose up` or `uvicorn aegisai.main:app --reload`).
2. Serve this folder (avoids `file://` issues with `fetch`):

   ```bash
   cd examples/demo-ui
   python3 -m http.server 8765
   ```

   Open `http://127.0.0.1:8765/`.

3. Set **API base URL** and optional **secret**; choose **Bearer** or **X-API-Key**.

## What you can do

- **Probes:** `GET /ready`, `/health`, `/version`, `/v1/policy`, `/v1/metrics` (JSON)
- **Collections:** `GET /v1/collections` — fills the RAG collection dropdown
- **Pipeline designer:** sensitivity (`public` … `regulated`), mode (`local_only` / `hybrid`), optional structured output presets
- **Experiment types:** image / document / video (with **video_sampling** options) / **Chroma RAG** (text + collection only)
- **Jobs:** build JSON from the form, `POST /v1/jobs` (optional **Idempotency-Key**), poll status, cancel, SSE stream (fetch + auth headers)
- **Output:** copy/clear, toast feedback, collapsible raw JSON editor

For full API detail use `/docs` on the running server.

## Attribution (footer)

Copyright and author links are **not** inlined in `index.html`. They are built at runtime from ES modules under **`internal/attribution/`** (`bootstrap.mjs` → `render.mjs` → `tokens.mjs`). Removing or splitting those files without replacing the footer breaks the intended credit surface; keep them when copying the Lab UI.
