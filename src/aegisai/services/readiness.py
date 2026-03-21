"""Dependency checks for Kubernetes-style readiness (inference backend + Chroma persistence)."""

from __future__ import annotations

from pathlib import Path

from aegisai.config import Settings
from aegisai.inference.protocol import InferenceBackend


def _ensure_chroma_writable(chroma_dir: Path) -> None:
    chroma_dir.mkdir(parents=True, exist_ok=True)
    probe = chroma_dir / ".aegisai_probe"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as e:
        msg = f"chroma persist dir not writable: {chroma_dir}"
        raise RuntimeError(msg) from e


async def readiness_details(settings: Settings, inference: InferenceBackend) -> dict[str, object]:
    """Raises on failure (inference unreachable, chroma not writable)."""
    _ensure_chroma_writable(settings.chroma_persist_dir)
    data = await inference.tags()
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
