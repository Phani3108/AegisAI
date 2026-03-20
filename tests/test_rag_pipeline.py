from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.rag import run_rag_pipeline
from aegisai.schemas.jobs import InputType, JobInput, JobRequest


@pytest.mark.asyncio
async def test_run_rag_pipeline_embed_retrieve_llm(tmp_path: Path) -> None:
    doc = tmp_path / "note.txt"
    doc.write_text(
        ("alpha beta gamma. " * 8 + "\n" + "second line about delta. " * 8 + "\n") * 2,
        encoding="utf-8",
    )
    uri = doc.resolve().as_uri()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/embeddings":
            return httpx.Response(200, json={"embedding": [0.2, 0.4, 0.4]})
        if request.url.path == "/api/chat":
            return httpx.Response(
                200,
                json={
                    "message": {"content": "synthetic rag answer"},
                    "prompt_eval_count": 3,
                    "eval_count": 7,
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    settings = Settings(
        ollama_base_url="http://ollama.test",
        llm_model="llama3.2",
        embed_model="nomic-embed-text",
        rag_chunk_size=64,
        rag_chunk_overlap=8,
        rag_top_k=2,
    )
    body = JobRequest(
        inputs=[
            JobInput(type=InputType.document_ref, uri=uri),
            JobInput(type=InputType.text, text="What mentions delta?"),
        ],
    )
    async with httpx.AsyncClient(transport=transport) as client:
        ollama = OllamaClient(settings.ollama_base_url, client, timeout_s=30.0)
        out = await run_rag_pipeline(body, settings, ollama)

    assert "synthetic" in out.answer.lower()
    assert out.chunk_count >= 1
    assert out.retrieval_ms >= 0
    assert out.llm_ms >= 0
