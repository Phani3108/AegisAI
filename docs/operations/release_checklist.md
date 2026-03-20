# Release Checklist

## Functional gate

- [ ] `scripts/qa_verify.sh` passes on main branch.
- [ ] Security/auth tests pass (API key and JWT mode).
- [ ] Durable job recovery tested by restart scenario.

## Platform gate

- [ ] Helm chart rendered successfully.
- [ ] Resource requests/limits reviewed for target cluster.
- [ ] HPA and PDB enabled with expected min/max.
- [ ] Persistence enabled for Chroma and job state path.

## Observability gate

- [ ] `/metrics` exposes retry/dead-letter and p95/p99 latency metrics.
- [ ] Request IDs appear in logs for API requests.
- [ ] Dashboard and alert rules updated for new metrics.

## Scale gate

- [ ] Latest scale/failover drill results documented in `docs/operations/scale_validation.md`.
- [ ] Known limits section in README is up to date.
- [ ] Rollback plan tested (previous image tag + Helm rollback).
