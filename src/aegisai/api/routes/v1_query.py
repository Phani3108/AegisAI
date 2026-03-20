from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from aegisai.api.openapi_extra import common_error_responses
from aegisai.ollama.client import OllamaClient
from aegisai.schemas.stream import StreamChatRequest

router = APIRouter()


@router.post(
    "/query",
    summary="Synchronous chat",
    description=(
        "Non-streaming Ollama `/api/chat` call. Bounded by **`AEGISAI_QUERY_TIMEOUT_S`** "
        "(see environment table in README)."
    ),
    responses={**common_error_responses(401, 502)},
)
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
        retry_attempts=settings.ollama_retry_attempts,
        retry_backoff_s=settings.ollama_retry_backoff_s,
    )
    try:
        return await ollama.chat(body.model, body.to_ollama_messages())
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"ollama query failed: {e!s}",
        ) from e
