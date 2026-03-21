from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEGISAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    inference_backend: str = Field(
        default="ollama",
        description="Inference driver: ollama (default); more backends planned for scale-out.",
    )
    vision_model: str = Field(default="llava")
    llm_model: str = Field(default="llama3.2")
    embed_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model for RAG (/api/embeddings).",
    )
    rag_chunk_size: int = Field(default=512, ge=64, le=8192)
    rag_chunk_overlap: int = Field(default=64, ge=0, le=2048)
    rag_top_k: int = Field(default=4, ge=1, le=32)
    ollama_timeout_s: float = Field(default=600.0)
    query_timeout_s: float = Field(
        default=120.0,
        ge=1.0,
        le=600.0,
        description="HTTP timeout for synchronous POST /v1/query (bounded chat).",
    )
    media_root: Path | None = Field(
        default=None,
        description="If set, image file:// paths must resolve under this directory.",
    )
    routing_policy_path: Path | None = Field(
        default=None,
        description="YAML routing policy; default config/routing_policy.yaml under repo root.",
    )
    chroma_persist_dir: Path = Field(
        default=Path("data/chroma"),
        description="Chroma persist dir (relative to CWD unless absolute).",
    )
    otel_enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry FastAPI instrumentation (install aegisai[otel]).",
    )
    api_key: str | None = Field(
        default=None,
        description="If set, /v1/* requires Authorization: Bearer <key> or X-API-Key.",
    )
    auth_mode: str = Field(
        default="api_key",
        description="Auth mode: api_key | jwt | both.",
    )
    jwt_secret: str | None = Field(
        default=None,
        description="HS256 secret for Bearer JWT mode.",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT algorithm for Bearer JWT mode.",
    )
    protect_ops_endpoints: bool = Field(
        default=False,
        description="If true, /ready and /metrics endpoints require authentication.",
    )
    max_concurrent_jobs: int = Field(
        default=8,
        ge=1,
        le=1024,
        description="Max pipeline jobs running at once; extra POST /v1/jobs returns 429.",
    )
    dlp_enabled: bool = Field(
        default=False,
        description="Enable regex DLP scan on hybrid job requests (text inputs).",
    )
    dlp_block_hybrid: bool = Field(
        default=True,
        description="If DLP finds patterns and mode is hybrid, reject job creation (400).",
    )
    log_json: bool = Field(
        default=False,
        description="Emit one JSON object per log line on stderr (for Loki/ELK/K8s).",
    )
    rate_limit_per_minute: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
        description=(
            "If set, cap /v1/* requests per client IP per rolling 60s (429 Too Many Requests)."
        ),
    )
    redis_url: str | None = Field(
        default=None,
        description=(
            "Optional Redis URL (redis://…). When set with pip install 'aegisai[redis]', "
            "Idempotency-Key mappings and per-IP rate limits are shared across replicas."
        ),
    )
    idempotency_ttl_seconds: int = Field(
        default=604800,
        ge=60,
        le=2_592_000,
        description="TTL (seconds) for Redis Idempotency-Key entries (default 7 days).",
    )
    job_retry_attempts: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Retry attempts for transient job failures before dead-letter marking.",
    )
    ollama_retry_attempts: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Retry attempts for transient Ollama transport/5xx failures.",
    )
    ollama_retry_backoff_s: float = Field(
        default=0.35,
        ge=0.0,
        le=5.0,
        description="Base backoff for Ollama retries (seconds), multiplied by attempt.",
    )
    connector_remote_enabled: bool = Field(
        default=False,
        description="Allow https:// and s3:// media/document URIs (allowlists required).",
    )
    connector_max_fetch_bytes: int = Field(
        default=50_000_000,
        ge=1024,
        le=500_000_000,
        description="Max bytes per remote fetch (HTTPS/S3).",
    )
    connector_fetch_timeout_s: float = Field(
        default=120.0,
        ge=5.0,
        le=3600.0,
        description="HTTP client timeout for connector GETs.",
    )
    connector_https_hosts_allowlist: str | None = Field(
        default=None,
        description=(
            "Comma-separated lowercase hostnames for https:// (final URL after redirects)."
        ),
    )
    connector_s3_bucket_allowlist: str | None = Field(
        default=None,
        description="Comma-separated S3 buckets for s3:// URIs (optional dep: aegisai[s3]).",
    )
    connector_ingest_max_concurrent: int = Field(
        default=8,
        ge=1,
        le=64,
        description="Max parallel source_uri fetches per POST /v1/collections/.../documents batch.",
    )
    asr_stub: bool = Field(
        default=True,
        description="If true, ASR returns a stub transcript (no external model).",
    )
    asr_stub_text: str = Field(
        default="[asr stub] configure AEGISAI_ASR_HTTP_URL or implement a real ASR backend",
        description="Transcript text used when asr_stub is true.",
    )
    asr_http_url: str | None = Field(
        default=None,
        description="Optional ASR over HTTP: POST wav as multipart file; JSON text + segments.",
    )
    asr_http_timeout_s: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        description="Timeout for ASR HTTP backend.",
    )


def get_settings() -> Settings:
    return Settings()
