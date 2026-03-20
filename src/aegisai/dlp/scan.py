"""Lightweight DLP-style pattern scan for hybrid-mode gate (prototype, not a compliance tool)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Conservative patterns for demo / pre-flight checks only.
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# 16-digit card groups with optional separators (spaces/dashes).
_CC_GROUPS = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")


@dataclass(frozen=True)
class DlpScanResult:
    kinds: tuple[str, ...]

    @property
    def has_findings(self) -> bool:
        return len(self.kinds) > 0


def scan_request_text(text: str) -> DlpScanResult:
    """Return finding kinds (deduped) for user-supplied text (prompts, RAG questions, etc.)."""
    if not (text or "").strip():
        return DlpScanResult(kinds=())
    kinds: list[str] = []
    if _SSN.search(text):
        kinds.append("ssn_like")
    if _CC_GROUPS.search(text):
        kinds.append("credit_card_like")
    # Dedupe while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for k in kinds:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return DlpScanResult(kinds=tuple(ordered))
