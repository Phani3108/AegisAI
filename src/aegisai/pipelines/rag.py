from __future__ import annotations

import math
import time
from dataclasses import dataclass

from aegisai.config import Settings
from aegisai.inference.protocol import InferenceBackend
from aegisai.pipelines.io_util import resolve_file_uri
from aegisai.pipelines.vision_steps import llm_answer_from_evidence, merge_token_hints
from aegisai.schemas.jobs import InputType, JobInput, JobRequest


@dataclass
class RagPipelineResult:
    answer: str
    ingest_ms: int
    retrieval_ms: int
    llm_ms: int
    chunk_count: int
    llm_model: str
    embed_model: str
    prompt_tokens_hint: int | None
    eval_tokens_hint: int | None


def pick_user_question(inputs: list[JobInput]) -> str:
    for item in inputs:
        if item.type == InputType.text and item.text:
            return item.text.strip()
    return "Summarize the document and list key facts."


def _first_document_uri(inputs: list[JobInput]) -> str:
    for item in inputs:
        if item.type == InputType.document_ref and item.uri:
            return item.uri
    raise ValueError("no document_ref with uri in inputs")


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if overlap >= size:
        overlap = max(0, size // 8)
    chunks: list[str] = []
    start = 0
    n = len(text)
    step = max(1, size - overlap)
    while start < n:
        chunks.append(text[start : start + size])
        start += step
    return chunks


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def run_rag_pipeline(
    request: JobRequest,
    settings: Settings,
    ollama: InferenceBackend,
) -> RagPipelineResult:
    t0 = time.perf_counter()
    uri = _first_document_uri(request.inputs)
    path = resolve_file_uri(uri, settings)
    raw = path.read_text(encoding="utf-8", errors="replace")
    user_question = pick_user_question(request.inputs)
    chunks = chunk_text(raw, settings.rag_chunk_size, settings.rag_chunk_overlap)
    if not chunks:
        raise ValueError("document is empty or whitespace only")
    ingest_ms = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    chunk_embeddings: list[tuple[str, list[float]]] = []
    for c in chunks:
        emb = await ollama.embed(settings.embed_model, c)
        chunk_embeddings.append((c, emb))

    q_emb = await ollama.embed(settings.embed_model, user_question)
    scored: list[tuple[float, str]] = []
    for text, emb in chunk_embeddings:
        scored.append((cosine_similarity(q_emb, emb), text))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [t for _, t in scored[: settings.rag_top_k]]
    context = "\n\n---\n\n".join(top)
    retrieval_ms = int((time.perf_counter() - t1) * 1000)

    t2 = time.perf_counter()
    answer, llm_body = await llm_answer_from_evidence(
        ollama,
        settings.llm_model,
        evidence_title="retrieved document excerpts",
        evidence_text=context,
        user_question=user_question,
        output_schema=request.output_schema,
    )
    llm_ms = int((time.perf_counter() - t2) * 1000)

    prompt_hint, eval_hint = merge_token_hints(llm_body)

    return RagPipelineResult(
        answer=answer,
        ingest_ms=ingest_ms,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        chunk_count=len(chunks),
        llm_model=settings.llm_model,
        embed_model=settings.embed_model,
        prompt_tokens_hint=prompt_hint,
        eval_tokens_hint=eval_hint,
    )
