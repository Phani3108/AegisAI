from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx


def run_once(client: httpx.Client, base_url: str) -> float:
    t0 = time.perf_counter()
    r = client.get(f"{base_url}/v1/policy")
    r.raise_for_status()
    return (time.perf_counter() - t0) * 1000.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture simple API latency baseline.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--out", default="docs/operations/benchmark_baseline.json")
    args = parser.parse_args()

    samples: list[float] = []
    with httpx.Client(timeout=args.timeout) as client:
        for _ in range(args.requests):
            samples.append(run_once(client, args.base_url.rstrip("/")))

    samples_sorted = sorted(samples)
    p50 = statistics.median(samples_sorted)
    p95_idx = max(0, min(len(samples_sorted) - 1, int(len(samples_sorted) * 0.95) - 1))
    p99_idx = max(0, min(len(samples_sorted) - 1, int(len(samples_sorted) * 0.99) - 1))
    out = {
        "base_url": args.base_url,
        "requests": args.requests,
        "latency_ms": {
            "min": round(samples_sorted[0], 2),
            "p50": round(p50, 2),
            "p95": round(samples_sorted[p95_idx], 2),
            "p99": round(samples_sorted[p99_idx], 2),
            "max": round(samples_sorted[-1], 2),
            "avg": round(sum(samples_sorted) / len(samples_sorted), 2),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
