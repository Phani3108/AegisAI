"""HTTPS and S3 read-only fetch with size caps and allowlists (P20)."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from aegisai.config import Settings
from aegisai.connectors.virus_scan import scan_fetched_payload


def _split_csv(s: str | None) -> frozenset[str]:
    if not s or not str(s).strip():
        return frozenset()
    return frozenset(x.strip().lower() for x in str(s).split(",") if x.strip())


def _check_size(data: bytes, settings: Settings) -> None:
    mx = int(settings.connector_max_fetch_bytes)
    if len(data) > mx:
        msg = f"fetched payload too large ({len(data)} bytes > {mx})"
        raise ValueError(msg)


async def fetch_https_bytes(uri: str, settings: Settings) -> bytes:
    if not settings.connector_remote_enabled:
        msg = "https URIs require AEGISAI_CONNECTOR_REMOTE_ENABLED=true"
        raise ValueError(msg)
    allowed = _split_csv(settings.connector_https_hosts_allowlist)
    if not allowed:
        msg = "https fetch requires non-empty AEGISAI_CONNECTOR_HTTPS_HOSTS_ALLOWLIST"
        raise ValueError(msg)
    timeout = httpx.Timeout(settings.connector_fetch_timeout_s)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(uri)
        r.raise_for_status()
        host = (r.url.host or "").lower()
        if host not in allowed:
            msg = f"final URL host {host!r} not in HTTPS allowlist"
            raise ValueError(msg)
        data = r.content
        ct = r.headers.get("content-type")
    _check_size(data, settings)
    scan_fetched_payload(data, content_type=ct, source=uri)
    return data


def fetch_s3_bytes(uri: str, settings: Settings) -> bytes:
    if not settings.connector_remote_enabled:
        msg = "s3 URIs require AEGISAI_CONNECTOR_REMOTE_ENABLED=true"
        raise ValueError(msg)
    try:
        import boto3  # type: ignore[import-untyped]
    except ImportError as e:
        msg = "s3:// URIs require: pip install 'aegisai[s3]'"
        raise RuntimeError(msg) from e
    parsed = urlparse(uri)
    if (parsed.scheme or "").lower() != "s3":
        raise ValueError(f"expected s3:// URI, got {uri!r}")
    bucket = (parsed.netloc or "").strip().lower()
    key = (parsed.path or "").lstrip("/")
    if not bucket or not key:
        raise ValueError(f"invalid s3 URI: {uri!r}")
    allowed_buckets = _split_csv(settings.connector_s3_bucket_allowlist)
    if not allowed_buckets:
        msg = "s3 fetch requires non-empty AEGISAI_CONNECTOR_S3_BUCKET_ALLOWLIST"
        raise ValueError(msg)
    if bucket not in allowed_buckets:
        msg = f"S3 bucket {bucket!r} not in allowlist"
        raise ValueError(msg)
    client = boto3.client("s3")
    obj = client.get_object(Bucket=bucket, Key=key)
    mx = int(settings.connector_max_fetch_bytes)
    body = obj["Body"].read(mx + 1)
    if len(body) > mx:
        msg = f"S3 object exceeds max fetch bytes ({mx})"
        raise ValueError(msg)
    scan_fetched_payload(body, content_type=None, source=uri)
    return bytes(body)
