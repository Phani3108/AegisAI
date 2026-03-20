from __future__ import annotations

import asyncio
import time
from typing import Any

import chromadb

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.rag import RagPipelineResult, pick_user_question
from aegisai.pipelines.vision_steps import llm_answer_from_evidence, merge_token_hints
from aegisai.rag_store.names import sanitize_collection_name
from aegisai.schemas.jobs import JobRequest


async def run_chroma_rag_pipeline(
    request: JobRequest,
    settings: Settings,
    ollama: OllamaClient,
    chroma: chromadb.PersistentClient,
) -> RagPipelineResult:
    name = (request.rag_collection or "").strip()
    if not name:
        raise ValueError("rag_collection is required")
    safe = sanitize_collection_name(name)
    user_question = pick_user_question(request.inputs)

    t0 = time.perf_counter()

    def _get():
        return chroma.get_collection(safe)

    try:
        col = await asyncio.to_thread(_get)
    except Exception as e:
        raise ValueError(f"Chroma collection not found: {safe!r}") from e

    q_emb = await ollama.embed(settings.embed_model, user_question)

    def _query():
        return col.query(
            query_embeddings=[q_emb],
            n_results=settings.rag_top_k,
            include=["documents"],
        )

    res: dict[str, Any] = await asyncio.to_thread(_query)
    docs = (res.get("documents") or [[]])[0] or []
    context = "\n\n---\n\n".join(d for d in docs if d)
    if not context.strip():
        context = "(no retrieved chunks; collection may be empty)"
    retrieval_ms = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    answer, llm_body = await llm_answer_from_evidence(
        ollama,
        settings.llm_model,
        evidence_title="retrieved excerpts from Chroma collection",
        evidence_text=context,
        user_question=user_question,
    )
    llm_ms = int((time.perf_counter() - t1) * 1000)

    prompt_hint, eval_hint = merge_token_hints(llm_body)

    return RagPipelineResult(
        answer=answer,
        ingest_ms=0,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        chunk_count=len(docs),
        llm_model=settings.llm_model,
        embed_model=settings.embed_model,
        prompt_tokens_hint=prompt_hint,
        eval_tokens_hint=eval_hint,
    )
