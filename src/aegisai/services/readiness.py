"""Dependency checks for Kubernetes-style readiness (Ollama + Chroma persistence)."""

from __future__ import annotations

from pathlib import Path

import httpx

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient


def _ensure_chroma_writable(chroma_dir: Path) -> None:
    chroma_dir.mkdir(parents=True, exist_ok=True)
    probe = chroma_dir / ".aegisai_probe"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as e:
        msg = f"chroma persist dir not writable: {chroma_dir}"
        raise RuntimeError(msg) from e


async def readiness_details(settings: Settings, http: httpx.AsyncClient) -> dict[str, object]:
    """Raises on failure (ollama unreachable, chroma not writable)."""
    _ensure_chroma_writable(settings.chroma_persist_dir)
    ollama = OllamaClient(
        settings.ollama_base_url,
        http,
        timeout_s=10.0,
        retry_attempts=settings.ollama_retry_attempts,
        retry_backoff_s=settings.ollama_retry_backoff_s,
    )
    data = await ollama.tags()
    raw_models = data.get("models") or []
    names: list[str] = []
    if isinstance(raw_models, list):
        for m in raw_models:
            if isinstance(m, dict) and "name" in m:
                names.append(str(m.get("name", "")))
    return {
        "status": "ready",
        "ollama": "ok",
        "models": names,
        "chroma": "ok",
    }
