#!/usr/bin/env python3
"""Benchmark v0: wall time + stage ms for one image job (requires running Ollama)."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from aegisai.benchmarks.image_v0 import run_image_benchmark


async def main() -> None:
    p = argparse.ArgumentParser(description="AegisAI benchmark v0 (image pipeline)")
    p.add_argument("image", type=Path, help="Path to image file")
    p.add_argument(
        "--question",
        default="",
        help="Optional user question (else default summary prompt is used)",
    )
    args = p.parse_args()
    report = await run_image_benchmark(args.image, question=args.question)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
