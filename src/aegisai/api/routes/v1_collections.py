from __future__ import annotations

import asyncio
import logging

import chromadb
from fastapi import APIRouter, HTTPException, Request

from aegisai.ollama.client import OllamaClient
from aegisai.rag_store.ingest import upsert_documents
from aegisai.rag_store.names import sanitize_collection_name
from aegisai.schemas.collections import (
    CollectionCreate,
    DocumentBatch,
    IngestResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _chroma(request: Request) -> chromadb.PersistentClient:
    c = getattr(request.app.state, "chroma", None)
    if c is None:
        raise HTTPException(status_code=503, detail="Chroma client not initialized")
    return c


@router.get("/collections")
async def list_collections(request: Request) -> dict:
    chroma = _chroma(request)

    def _list():
        cols = chroma.list_collections()
        return [c.name for c in cols]

    names = await asyncio.to_thread(_list)
    return {"collections": names}


@router.post("/collections")
async def create_collection(body: CollectionCreate, request: Request) -> dict:
    chroma = _chroma(request)
    safe = sanitize_collection_name(body.name)

    def _create():
        chroma.get_or_create_collection(safe, metadata={"hnsw:space": "cosine"})

    await asyncio.to_thread(_create)
    logger.info("collection_created name=%s", safe)
    return {"name": safe}


@router.post("/collections/{name}/documents", response_model=IngestResponse)
async def ingest_documents_route(
    name: str,
    body: DocumentBatch,
    request: Request,
) -> IngestResponse:
    chroma = _chroma(request)
    settings = request.app.state.settings
    http = request.app.state.http
    ollama = OllamaClient(settings.ollama_base_url, http, timeout_s=settings.ollama_timeout_s)
    items = [(d.id, d.text, d.metadata) for d in body.documents]
    n = await upsert_documents(chroma, name, settings, ollama, items)
    safe = sanitize_collection_name(name)
    return IngestResponse(chunks_added=n, collection=safe)


@router.delete("/collections/{name}")
async def delete_collection(name: str, request: Request) -> dict:
    chroma = _chroma(request)
    safe = sanitize_collection_name(name)

    def _delete() -> None:
        chroma.delete_collection(safe)

    try:
        await asyncio.to_thread(_delete)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"collection not found: {e!s}") from e
    return {"deleted": safe}
