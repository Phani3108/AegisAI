# Benchmarks

## v0 (image pipeline)

Requires Ollama and pulled models (see root `README.md`):

```bash
python benchmarks/run_v0.py /path/to/image.png --question "Optional question"
```

Prints JSON with `vision_ms`, `llm_ms`, `wall_ms`, and token hints from Ollama.

The same logic lives in-package as `aegisai.benchmarks.run_image_benchmark` (CI covers it via `tests/test_benchmark_image_v0.py`).

## Next

- Versioned **datasets** (checksums in manifest)
- **Artifacts** under `runs/benchmarks/<date-or-git-sha>/` (per root `.gitignore`)

See `planning.md` §5.6 for the full benchmark specification.
