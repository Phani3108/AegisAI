from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx


class OllamaClient:
    """Thin async client for Ollama HTTP API (/api/chat, /api/tags)."""

    def __init__(
        self,
        base_url: str,
        http: httpx.AsyncClient,
        *,
        timeout_s: float = 600.0,
        retry_attempts: int = 0,
        retry_backoff_s: float = 0.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._http = http
        self._timeout = timeout_s
        self._retry_attempts = max(0, int(retry_attempts))
        self._retry_backoff_s = max(0.0, float(retry_backoff_s))

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            return code in (429, 500, 502, 503, 504)
        return False

    async def _with_retries(self, fn):
        attempts = self._retry_attempts + 1
        last: Exception | None = None
        for i in range(attempts):
            try:
                return await fn()
            except Exception as e:  # noqa: BLE001
                last = e
                if i >= attempts - 1 or not self._is_transient(e):
                    raise
                await asyncio.sleep(self._retry_backoff_s * (i + 1))
        if last is not None:
            raise last

    async def tags(self) -> dict:
        async def _call():
            r = await self._http.get(f"{self._base}/api/tags", timeout=30.0)
            r.raise_for_status()
            return r.json()

        return await self._with_retries(_call)

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
        async def _call():
            r = await self._http.post(
                f"{self._base}/api/chat",
                json=payload,
                timeout=self._timeout,
            )
            r.raise_for_status()
            return r.json()

        return await self._with_retries(_call)

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
        async def _call():
            r = await self._http.post(
                f"{self._base}/api/embeddings",
                json={"model": model, "prompt": prompt},
                timeout=self._timeout,
            )
            r.raise_for_status()
            return r.json()

        data = await self._with_retries(_call)
        emb = data.get("embedding")
        if not isinstance(emb, list):
            raise ValueError("ollama /api/embeddings returned no embedding list")
        return [float(x) for x in emb]

    @staticmethod
    def message_content(body: dict) -> str:
        from aegisai.inference.messages import chat_message_content

        return chat_message_content(body)
