from __future__ import annotations

import asyncio
from typing import Any

import chromadb

from aegisai.config import Settings
from aegisai.inference.protocol import InferenceBackend
from aegisai.pipelines.rag import chunk_text
from aegisai.rag_store.names import sanitize_collection_name


def _flatten_metadata(meta: dict[str, Any] | None) -> dict[str, str | int | float | bool]:
    out: dict[str, str | int | float | bool] = {}
    if not meta:
        return out
    for k, v in meta.items():
        key = str(k)[:256]
        if isinstance(v, bool):
            out[key] = v
        elif isinstance(v, int | float):
            out[key] = v
        else:
            out[key] = str(v)[:4096]
    return out


async def upsert_documents(
    chroma: chromadb.PersistentClient,
    collection_name: str,
    settings: Settings,
    ollama: InferenceBackend,
    items: list[tuple[str, str, dict[str, Any] | None]],
) -> int:
    """
    Chunk + embed each logical document and add to Chroma.
    items: (source_id, full_text, optional_metadata)
    Returns number of chunks written.
    """
    safe = sanitize_collection_name(collection_name)

    def _get_col():
        return chroma.get_or_create_collection(
            safe,
            metadata={"hnsw:space": "cosine"},
        )

    col = await asyncio.to_thread(_get_col)
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int | float | bool]] = []

    for source_id, text, meta in items:
        base_meta = _flatten_metadata(meta)
        chunks = chunk_text(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
        if not chunks:
            continue
        for idx, ch in enumerate(chunks):
            emb = await ollama.embed(settings.embed_model, ch)
            cid = f"{source_id}__{idx}"
            ids.append(cid)
            embeddings.append(emb)
            documents.append(ch)
            chunk_meta = {
                **base_meta,
                "source_id": source_id[:512],
                "chunk_index": idx,
            }
            metadatas.append(chunk_meta)

    if not ids:
        return 0

    def _add():
        col.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    await asyncio.to_thread(_add)
    return len(ids)
