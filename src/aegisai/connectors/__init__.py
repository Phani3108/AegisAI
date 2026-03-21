"""Read-only remote ingest connectors (HTTPS, S3) + virus-scan hook stub (P20)."""

from aegisai.connectors.fetch import fetch_https_bytes, fetch_s3_bytes
from aegisai.connectors.virus_scan import scan_fetched_payload

__all__ = [
    "fetch_https_bytes",
    "fetch_s3_bytes",
    "scan_fetched_payload",
]
