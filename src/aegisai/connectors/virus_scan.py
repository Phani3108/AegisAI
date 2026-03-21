"""Virus-scan hook for fetched payloads (integrate AV here; default no-op)."""

from __future__ import annotations


def scan_fetched_payload(
    data: bytes,
    *,
    content_type: str | None,
    source: str,
) -> None:
    """
    Called after a successful remote fetch and before bytes are written to temp / parsed.

    Raise ValueError with a clear message to reject the payload.
    Default implementation is a no-op for local/dev; wire ClamAV, Defender API, etc. here.
    """
    _ = data, content_type, source
