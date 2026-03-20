#!/usr/bin/env python3
"""
Minimal LoRA / PEFT training entrypoint (stub).

Install training deps in a dedicated venv, e.g.:
  pip install peft transformers datasets accelerate torch

See docs/fine_tune/PLAYBOOK.md for dataset and safety requirements.
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    p = argparse.ArgumentParser(description="LoRA fine-tuning stub for AegisAI")
    p.add_argument("--base-model", default="meta-llama/Llama-3.2-1B-Instruct")
    p.add_argument("--dataset", default="", help="Path or HF dataset id")
    p.add_argument(
        "--execute",
        action="store_true",
        help="Attempt import of training stack (not implemented beyond checks).",
    )
    args = p.parse_args()

    if not args.execute:
        print("dry-run OK")
        print(f"  base_model={args.base_model!r}")
        print(f"  dataset={args.dataset!r}")
        print("Re-run with --execute after installing peft/transformers/torch (see PLAYBOOK).")
        return 0

    try:
        import peft  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as e:
        print("Missing training dependencies:", e, file=sys.stderr)
        print("pip install peft transformers datasets accelerate torch", file=sys.stderr)
        return 2

    print("Training loop not implemented in-repo yet; use as a scaffold only.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
