#!/usr/bin/env bash
# Full local QA gate: lint, tests (verbose + coverage of failures), package build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONWARNINGS="${PYTHONWARNINGS:-default}"
PY="${PYTHON:-python3}"

echo "==> ruff"
"$PY" -m ruff check src tests

echo "==> pytest (fail-safe TB, durations)"
"$PY" -m pytest -v --tb=short --durations=15

echo "==> ci_gate (pytest passthrough)"
"$PY" scripts/ci_gate.py

echo "==> compileall"
"$PY" -m compileall -q src

echo "==> build"
"$PY" -m build

echo "=== QA OK ==="
