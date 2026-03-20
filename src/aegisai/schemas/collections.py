from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class DocumentItem(BaseModel):
    id: str = Field(min_length=1, max_length=512)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] | None = None


class DocumentBatch(BaseModel):
    documents: list[DocumentItem] = Field(min_length=1, max_length=500)


class IngestResponse(BaseModel):
    chunks_added: int
    collection: str
