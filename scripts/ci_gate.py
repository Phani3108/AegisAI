#!/usr/bin/env python3
"""
CI gate: runs pytest (required). Benchmark harness is exercised via
tests/test_benchmark_image_v0.py (no live Ollama).

Extend later with coverage thresholds or benchmark regression thresholds.
"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short"], check=False)
    return int(r.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
