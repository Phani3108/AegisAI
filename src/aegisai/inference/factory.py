"""Construct the active inference backend from settings (multi-backend scale path)."""

from __future__ import annotations

import httpx

from aegisai.config import Settings
from aegisai.inference.protocol import InferenceBackend
from aegisai.ollama.client import OllamaClient


def create_inference_backend(
    settings: Settings,
    http: httpx.AsyncClient,
    *,
    chat_timeout_s: float | None = None,
    retry_attempts: int | None = None,
    retry_backoff_s: float | None = None,
) -> InferenceBackend:
    """Return configured backend. Today only ``ollama``; raises if unknown."""
    name = (settings.inference_backend or "ollama").strip().lower()
    if name != "ollama":
        msg = f"Unknown AEGISAI_INFERENCE_BACKEND={name!r}; supported: ollama"
        raise ValueError(msg)
    to = (
        float(chat_timeout_s)
        if chat_timeout_s is not None
        else float(settings.ollama_timeout_s)
    )
    return OllamaClient(
        settings.ollama_base_url,
        http,
        timeout_s=to,
        retry_attempts=int(
            retry_attempts if retry_attempts is not None else settings.ollama_retry_attempts
        ),
        retry_backoff_s=float(
            retry_backoff_s if retry_backoff_s is not None else settings.ollama_retry_backoff_s
        ),
    )
