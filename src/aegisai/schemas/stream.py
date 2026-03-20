from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StreamChatMessage(BaseModel):
    role: str
    content: str
    images: list[str] | None = Field(
        default=None,
        description="Optional base64-encoded images for multimodal models.",
    )


class StreamChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "llama3.2",
                "messages": [{"role": "user", "content": "Say hello in one sentence."}],
            }
        }
    )

    model: str = Field(min_length=1)
    messages: list[StreamChatMessage] = Field(min_length=1)

    def to_ollama_messages(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in self.messages:
            d: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.images:
                d["images"] = m.images
            out.append(d)
        return out
