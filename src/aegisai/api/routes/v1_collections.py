from __future__ import annotations

import asyncio
import logging

import chromadb
from fastapi import APIRouter, HTTPException, Request

from aegisai.api.openapi_extra import common_error_responses
from aegisai.config import Settings
from aegisai.pipelines.io_util import materialize_uri
from aegisai.rag_store.ingest import upsert_documents
from aegisai.rag_store.names import sanitize_collection_name
from aegisai.schemas.collections import (
    CollectionCreate,
    DocumentBatch,
    DocumentItem,
    IngestResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _resolved_document_text(
    d: DocumentItem,
    settings: Settings,
) -> tuple[str, str, dict | None]:
    raw_t = (d.text or "").strip()
    if raw_t:
        return d.id, raw_t, d.metadata
    uri = (d.source_uri or "").strip()
    path, temps = await materialize_uri(uri, settings)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return d.id, text, d.metadata
    finally:
        for p in temps:
            p.unlink(missing_ok=True)


def _chroma(request: Request) -> chromadb.PersistentClient:
    c = getattr(request.app.state, "chroma", None)
    if c is None:
        raise HTTPException(status_code=503, detail="Chroma client not initialized")
    return c


@router.get(
    "/collections",
    summary="List Chroma collections",
    responses={**common_error_responses(401, 503)},
)
async def list_collections(request: Request) -> dict:
    chroma = _chroma(request)

    def _list():
        cols = chroma.list_collections()
        return [c.name for c in cols]

    names = await asyncio.to_thread(_list)
    return {"collections": names}


@router.post(
    "/collections",
    summary="Create collection",
    responses={**common_error_responses(401, 503)},
)
async def create_collection(body: CollectionCreate, request: Request) -> dict:
    chroma = _chroma(request)
    safe = sanitize_collection_name(body.name)

    def _create():
        chroma.get_or_create_collection(safe, metadata={"hnsw:space": "cosine"})

    await asyncio.to_thread(_create)
    logger.info("collection_created name=%s", safe)
    return {"name": safe}


@router.post(
    "/collections/{name}/documents",
    response_model=IngestResponse,
    summary="Ingest documents",
    responses={**common_error_responses(401, 503)},
)
async def ingest_documents_route(
    name: str,
    body: DocumentBatch,
    request: Request,
) -> IngestResponse:
    chroma = _chroma(request)
    settings = request.app.state.settings
    ollama = request.app.state.inference
    sem = asyncio.Semaphore(settings.connector_ingest_max_concurrent)

    async def one(doc: DocumentItem) -> tuple[str, str, dict | None]:
        async with sem:
            return await _resolved_document_text(doc, settings)

    resolved = await asyncio.gather(*(one(d) for d in body.documents))
    items = [(i, t, m) for i, t, m in resolved]
    n = await upsert_documents(chroma, name, settings, ollama, items)
    safe = sanitize_collection_name(name)
    return IngestResponse(chunks_added=n, collection=safe)


@router.delete(
    "/collections/{name}",
    summary="Delete collection",
    responses={**common_error_responses(401, 404, 503)},
)
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
