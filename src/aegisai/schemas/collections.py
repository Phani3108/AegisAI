from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class CollectionCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class DocumentItem(BaseModel):
    id: str = Field(min_length=1, max_length=512)
    text: str | None = None
    source_uri: str | None = Field(
        default=None,
        description="Fetch UTF-8 text from file://, https://, or s3://; exclusive with text.",
    )
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> DocumentItem:
        t = (self.text or "").strip()
        u = (self.source_uri or "").strip()
        if bool(t) == bool(u):
            raise ValueError("each document requires exactly one of text or source_uri")
        return self


class DocumentBatch(BaseModel):
    documents: list[DocumentItem] = Field(
        min_length=1,
        max_length=2000,
        description="Up to 2000 documents per batch (P20); use source_uri for remote fetch.",
    )


class IngestResponse(BaseModel):
    chunks_added: int
    collection: str
