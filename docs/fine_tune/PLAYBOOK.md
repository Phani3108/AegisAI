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

## Next implementation steps (for this repo)

- Add `experiments/` with a minimal LoRA training script template.
- Wire CI (optional) to run `pytest` + benchmark smoke on PRs.

This file is intentionally high-level until you choose a base model and hosting path (Ollama import vs HF weights).
