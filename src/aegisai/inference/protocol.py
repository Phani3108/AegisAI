"""Pluggable inference surface (chat, embed, model listing) for scale-out backends."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class InferenceBackend(Protocol):
    """Contract implemented by Ollama today; vLLM / cloud adapters later."""

    async def tags(self) -> dict[str, Any]:
        """Backend-specific model list payload (Ollama: GET /api/tags shape)."""
        ...

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        stream: bool = False,
        response_format: str | None = None,
    ) -> dict[str, Any]:
        ...

    def chat_stream(
        self, model: str, messages: list[dict[str, Any]]
    ) -> AsyncIterator[str]:
        ...

    async def embed(self, model: str, prompt: str) -> list[float]:
        ...
