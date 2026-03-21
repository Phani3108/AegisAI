from __future__ import annotations

import asyncio
import base64
import os
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from aegisai.config import Settings
from aegisai.connectors.fetch import fetch_https_bytes, fetch_s3_bytes


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


async def materialize_uri(uri: str, settings: Settings) -> tuple[Path, list[Path]]:
    """
    Resolve URI to a local Path. For file:// returns the resolved file and no temps.
    For https:// and s3:// fetches bytes (allowlists + caps), writes a temp file;
    caller must unlink paths in the returned temp list.
    """
    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()
    if scheme == "file":
        return resolve_file_uri(uri, settings), []
    if scheme in ("http", "https"):
        data = await fetch_https_bytes(uri, settings)
    elif scheme == "s3":
        data = await asyncio.to_thread(fetch_s3_bytes, uri, settings)
    else:
        raise ValueError(
            f"unsupported URI scheme {scheme!r} in {uri!r} "
            "(supported: file://, https:// with allowlist, s3:// with allowlist + aegisai[s3])"
        )
    ext = Path(unquote(parsed.path)).suffix[:16] or ".bin"
    fd, name = tempfile.mkstemp(prefix="aegisai_fetch_", suffix=ext)
    os.close(fd)
    tmp = Path(name)
    tmp.write_bytes(data)
    return tmp, [tmp]


def file_to_image_base64(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")
