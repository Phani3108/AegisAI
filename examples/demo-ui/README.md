# AegisAI demo UI (static)

Minimal **single-page** helper to try the API from a browser without curl.
Phase 10+ refresh adds a clean white theme and better operator-focused controls.

## How to run

1. Start AegisAI (e.g. `docker compose up` or `uvicorn aegisai.main:app --reload`).
2. Open **`index.html`** in a browser **or** serve the folder (avoids `file://` CORS issues):

   ```bash
   cd examples/demo-ui
   python3 -m http.server 8765
   ```

   Then open `http://127.0.0.1:8765/`.

3. Set **API base URL** (default `http://127.0.0.1:8000`) and optional **API key** to match your server.
   You can choose auth mode as **Authorization: Bearer** or **X-API-Key**.
4. Use:
   - **Check /ready** for backend readiness
   - **Load /v1/policy** for routing visibility
   - **Create Job** and **Refresh Job**
   - **Cancel Job** for running jobs
  - **Start /events stream** for live SSE event feed (header-capable fetch stream; works with auth)
   - **Start Auto Refresh** to poll job status every N seconds
5. You can copy response JSON, clear output, and beautify request JSON from the built-in controls.

## Included UX elements

- White-background card layout for readability
- Connection status pill (ready/not-ready)
- Sample request + beautify
- Structured payload builder (image / document / video templates)
- Job cancel action
- Live SSE event stream viewer for `GET /v1/jobs/{id}/events` with auth headers
- Job polling controls (off/2s/5s/10s)
- Response copy/clear actions and request timestamp metadata

This is a **debug / demo** surface, not a production console. For full API detail use `/docs`.
