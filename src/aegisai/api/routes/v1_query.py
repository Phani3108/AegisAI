from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from aegisai.ollama.client import OllamaClient
from aegisai.schemas.stream import StreamChatRequest

router = APIRouter()


@router.post("/query")
async def sync_query(request: Request, body: StreamChatRequest) -> dict:
    """
    Synchronous bounded chat: full Ollama `/api/chat` JSON response (non-streaming).
    Uses `AEGISAI_QUERY_TIMEOUT_S` instead of the long job timeout.
    """
    settings = request.app.state.settings
    http = request.app.state.http
    ollama = OllamaClient(
        settings.ollama_base_url,
        http,
        timeout_s=settings.query_timeout_s,
    )
    try:
        return await ollama.chat(body.model, body.to_ollama_messages())
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"ollama query failed: {e!s}",
        ) from e
