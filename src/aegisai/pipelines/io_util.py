from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import unquote, urlparse

from aegisai.config import Settings


def resolve_file_uri(uri: str, settings: Settings) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"unsupported URI scheme (expected file://): {uri!r}")
    path = Path(unquote(parsed.path))
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    if settings.media_root is not None:
        root = settings.media_root.resolve()
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as e:
            raise ValueError(f"path must be under media_root {root}: {resolved}") from e
    return path.resolve()


def file_to_image_base64(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")
