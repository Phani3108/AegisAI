from __future__ import annotations

import re


def sanitize_collection_name(name: str) -> str:
    """
    Chroma requires 3–512 chars from [a-zA-Z0-9._-], starting and ending with [a-zA-Z0-9].
    """
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._-") or "collection"
    if len(cleaned) > 120:
        cleaned = cleaned[:120]
    cleaned = cleaned.strip("._-") or "collection"
    while cleaned and not cleaned[0].isalnum():
        cleaned = cleaned[1:]
    while cleaned and not cleaned[-1].isalnum():
        cleaned = cleaned[:-1]
    if not cleaned:
        cleaned = "collection"
    while len(cleaned) < 3:
        cleaned = cleaned + "0"
    if len(cleaned) > 512:
        cleaned = cleaned[:512]
        while cleaned and not cleaned[-1].isalnum():
            cleaned = cleaned[:-1]
        if len(cleaned) < 3:
            cleaned = (cleaned + "000")[:3]
    return cleaned
