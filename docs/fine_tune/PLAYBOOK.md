# Fine-tuning playbook (stub)

Use this when you promote from **Phase 1 RAG / local inference** to **domain-tuned** models.

## Prerequisites

- A **dataset manifest** (JSON or DVC pointer): approved-for-training label, checksum, license.
- **Hardware**: GPU with enough VRAM for QLoRA on your base model class.
- **Benchmark gate**: `benchmarks/` harness must run before/after; promote only on agreed deltas.

## Suggested stack

- **PEFT / LoRA** (Hugging Face `peft`, `trl`) on top of the same model family you serve via Ollama or vLLM.
- **Experiment tracking**: MLflow or DVC for dataset hash + hyperparameters + eval scores.
- **Artifacts**: versioned adapters (not silent overwrite of baselines); register in your model registry doc.

## Safety

- Do not train on **regulated** or **unapproved** corpora.
- Keep a **frozen eval set** that never appears in training.

## Executable stub (this repo)

- [`experiments/train_lora.py`](../../experiments/train_lora.py) — `python experiments/train_lora.py` (dry-run) or `--execute` to verify imports after installing `peft` / `transformers` / `torch`. The training loop is **not** implemented; treat as a scaffold.

## CI / benchmark gate

- GitHub Actions runs **ruff**, **pytest**, and [`scripts/ci_gate.py`](../../scripts/ci_gate.py) on pushes/PRs to `main` (see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)).
- Extend `scripts/ci_gate.py` later with coverage floors or benchmark regression thresholds.

This file stays high-level until you choose a base model and hosting path (Ollama import vs HF weights).
