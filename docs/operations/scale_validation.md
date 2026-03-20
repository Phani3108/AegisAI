# Scale and Failover Validation

This runbook defines a repeatable validation cycle before production releases.

## Preconditions

- Helm values use persistence, HPA, and PDB defaults from `deploy/helm/aegisai/values.yaml`.
- At least 2 replicas are running.
- Redis is configured when multi-replica idempotency/cancellation behavior is required.

## Load validation (baseline)

1. Warm up with 20 low-cost requests (`GET /v1/policy`, `GET /v1/metrics`).
2. Run a 10-minute steady load:
   - 70% `POST /v1/jobs` (small image/document payloads)
   - 20% `GET /v1/jobs/{id}`
   - 10% `GET /v1/jobs/{id}/events`
3. Capture:
   - p95 and p99 latency from `aegisai_job_latency_ms_p95`/`p99`
   - Error rate (`5xx`, `429`)
   - Queue health (`aegisai_jobs_in_flight`)

## Failover drill

1. Start continuous job submission (at least 2 minutes).
2. Delete one pod manually.
3. Verify:
   - No API outage from ingress perspective.
   - Existing jobs remain queryable.
   - New jobs can still be created.
4. Restart the API deployment and validate startup recovery:
   - queued/running jobs recover on restart
   - events remain available for existing jobs

## Exit criteria

- No data-loss symptoms for accepted jobs.
- No sustained >2% 5xx during steady load.
- p95/p99 remain within agreed service SLO for your environment.
