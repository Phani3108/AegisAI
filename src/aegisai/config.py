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


def get_settings() -> Settings:
    return Settings()
