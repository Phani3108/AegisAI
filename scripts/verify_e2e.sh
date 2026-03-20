#!/usr/bin/env bash
# Deep verification: lint, byte-compile, tests, optional wheel build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

: "${PYTHON:=python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

echo "==> ruff"
"$PYTHON" -m ruff check src tests

echo "==> compileall"
"$PYTHON" -m compileall -q src

echo "==> pytest (verbose)"
"$PYTHON" -m pytest -v --tb=short

if "$PYTHON" -m pip show build >/dev/null 2>&1; then
  echo "==> wheel/sdist build"
  "$PYTHON" -m build --no-isolation 2>/dev/null || "$PYTHON" -m build
  echo "Build artifacts in dist/"
else
  echo "==> (optional) pip install build && python -m build"
fi

echo "==> OK"
