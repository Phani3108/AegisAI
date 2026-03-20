# AegisAI demo UI (static)

Minimal **single-page** helper to try the API from a browser without curl.

## How to run

1. Start AegisAI (e.g. `docker compose up` or `uvicorn aegisai.main:app --reload`).
2. Open **`index.html`** in a browser **or** serve the folder (avoids `file://` CORS issues):

   ```bash
   cd examples/demo-ui
   python3 -m http.server 8765
   ```

   Then open `http://127.0.0.1:8765/`.

3. Set **API base URL** (default `http://127.0.0.1:8000`) and optional **API key** to match your server.
4. Use **Load policy** to view routing rules, **Create sample job** for a placeholder body (edit **`file://` URI** to a real path on the **API server**), then **Refresh job** once you have a job ID.

This is a **debug / demo** surface, not a production console. For full API detail use `/docs`.
