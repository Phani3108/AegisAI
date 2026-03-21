from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from aegisai.api.openapi_extra import common_error_responses
from aegisai.schemas.stream import StreamChatRequest

router = APIRouter()


@router.post(
    "/stream/chat",
    summary="SSE streaming chat",
    description=(
        "Proxies Ollama streaming chat as **text/event-stream** "
        "(`data:` lines; stream ends with `[DONE]`)."
    ),
    responses={
        **common_error_responses(401),
        200: {
            "description": "SSE stream",
            "content": {"text/event-stream": {}},
        },
    },
    response_class=StreamingResponse,
)
async def stream_chat(request: Request, body: StreamChatRequest) -> StreamingResponse:
    """SSE proxy of Ollama `/api/chat` with `stream: true` (NDJSON lines as `data:` events)."""
    ollama = request.app.state.inference

    async def gen():
        try:
            async for line in ollama.chat_stream(body.model, body.to_ollama_messages()):
                yield f"data: {line}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
