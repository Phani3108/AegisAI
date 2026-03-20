from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx


class OllamaClient:
    """Thin async client for Ollama HTTP API (/api/chat, /api/tags)."""

    def __init__(self, base_url: str, http: httpx.AsyncClient, *, timeout_s: float = 600.0) -> None:
        self._base = base_url.rstrip("/")
        self._http = http
        self._timeout = timeout_s

    async def tags(self) -> dict:
        r = await self._http.get(f"{self._base}/api/tags", timeout=30.0)
        r.raise_for_status()
        return r.json()

    async def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        stream: bool = False,
        response_format: str | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": stream}
        if response_format:
            payload["format"] = response_format
        r = await self._http.post(
            f"{self._base}/api/chat",
            json=payload,
            timeout=self._timeout,
        )
        r.raise_for_status()
        return r.json()

    async def chat_stream(self, model: str, messages: list[dict]) -> AsyncIterator[str]:
        """Yields newline-delimited JSON chunks from Ollama when stream=true."""
        async with self._http.stream(
            "POST",
            f"{self._base}/api/chat",
            json={"model": model, "messages": messages, "stream": True},
            timeout=self._timeout,
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line:
                    yield line

    async def embed(self, model: str, prompt: str) -> list[float]:
        r = await self._http.post(
            f"{self._base}/api/embeddings",
            json={"model": model, "prompt": prompt},
            timeout=self._timeout,
        )
        r.raise_for_status()
        data = r.json()
        emb = data.get("embedding")
        if not isinstance(emb, list):
            raise ValueError("ollama /api/embeddings returned no embedding list")
        return [float(x) for x in emb]

    @staticmethod
    def message_content(body: dict) -> str:
        msg = body.get("message") or {}
        return (msg.get("content") or "").strip()
