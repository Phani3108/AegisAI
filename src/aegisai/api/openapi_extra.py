"""Shared OpenAPI / docs helpers (error schemas, tag copy)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

OPENAPI_TAGS: list[dict[str, Any]] = [
    {
        "name": "health",
        "description": (
            "Process and probes; `/live` and `/ready` are unauthenticated (Kubernetes-friendly)."
        ),
    },
    {
        "name": "jobs",
        "description": (
            "Async multimodal jobs, policy, `/v1` readiness, cancel, SSE/WebSocket progress, audit."
        ),
    },
    {
        "name": "collections",
        "description": "Chroma collection CRUD and document ingest for persistent RAG.",
    },
    {
        "name": "stream",
        "description": "Server-Sent Events proxy to Ollama streaming chat.",
    },
    {
        "name": "query",
        "description": "Synchronous bounded chat against Ollama (non-streaming).",
    },
    {
        "name": "metrics",
        "description": "Prometheus scrape (`GET /metrics`) and JSON counters under `/v1/metrics`.",
    },
]


class HTTPErrorBody(BaseModel):
    """Typical FastAPI/Starlette error JSON (`HTTPException` / validation)."""

    detail: Annotated[
        str | list[Any],
        Field(
            description="Human-readable message or list of validation errors.",
            examples=["unauthorized"],
        ),
    ]


def common_error_responses(
    *codes: int,
) -> dict[int | str, dict[str, Any]]:
    """Attach standard JSON error body to route `responses=` for OpenAPI."""
    desc = {
        400: "Bad request (policy, DLP, or validation).",
        401: "Missing or invalid API key when `AEGISAI_API_KEY` is set.",
        404: "Resource not found.",
        429: "Too many requests (concurrency cap or per-IP rate limit).",
        500: "Internal error.",
        502: "Upstream (e.g. Ollama) failure.",
        503: "Service not ready (dependencies unavailable).",
    }
    out: dict[int | str, dict[str, Any]] = {}
    for c in codes:
        label = desc.get(c, "Error.")
        out[c] = {
            "description": label,
            "model": HTTPErrorBody,
        }
    return out
