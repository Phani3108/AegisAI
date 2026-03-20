#!/usr/bin/env python3
"""
CI benchmark gate: runs the test suite (required) and exits non-zero on failure.
Extend later with coverage thresholds or benchmark regression checks.
"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short"], check=False)
    return int(r.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
