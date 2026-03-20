# ADR 0001: Python FastAPI control plane

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

AegisAI needs an HTTP API for job creation, health checks, future streaming, and OpenAPI-first contracts. The stack must integrate cleanly with local inference (Ollama initially), Python-native ML utilities (vision, RAG, benchmarks), and observability libraries.

## Decision

Use **Python 3.11+** with **FastAPI** and **Uvicorn** as the default API server. Package the application as an installable project (`pyproject.toml`, `src/aegisai/` layout). Job and event schemas are defined with **Pydantic v2** and exposed via auto-generated OpenAPI.

## Consequences

**Positive:**

- Fast iteration on JSON schemas and validation aligned with `planning.md`.
- Large ecosystem for ML, async HTTP (httpx), and later OTEL/RAG integrations.

**Negative:**

- If a component is later rewritten in Rust/Go for hot paths, maintain clear IPC or sidecar boundaries so the FastAPI service remains orchestration, not the compute bottleneck.

**Mitigation:**

- Keep heavy inference in Ollama/vLLM workers; the API process should stay thin (routing, policy, orchestration, metrics).
