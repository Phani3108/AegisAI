# Minimal Helm chart (T2 sketch)

- **Image**: set `image.repository` / `image.tag` to your registry build (this repo does not publish a default image).
- **Ollama**: point `AEGISAI_OLLAMA_BASE_URL` at an in-cluster `Service` or sidecar; the default `values.yaml` assumes a service named `ollama` on port `11434`.
- **Chroma**: enable `persistence.enabled` and size `persistence.size` for durable vector storage.

```bash
helm upgrade --install aegisai ./deploy/helm/aegisai \
  --set image.repository=your.registry/aegisai \
  --set image.tag=main
```

See root `README.md` for required environment variables and optional API key / DLP flags.
