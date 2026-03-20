# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AEGISAI_CHROMA_PERSIST_DIR=/data/chroma \
    AEGISAI_ROUTING_POLICY_PATH=/app/config/routing_policy.yaml

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir .

VOLUME ["/data/chroma"]
EXPOSE 8000

CMD ["uvicorn", "aegisai.main:app", "--host", "0.0.0.0", "--port", "8000"]
