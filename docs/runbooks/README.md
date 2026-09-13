# Incident Runbooks

This directory contains incident response runbooks for the highest-frequency
operability failures in this repository.

## Incident Index

- Startup failure: `docs/runbooks/startup-failure.md`
- API quota or rate limit incident: `docs/runbooks/api-quota-rate-limit.md`
- Configuration error: `docs/runbooks/config-error.md`
- Degraded performance: `docs/runbooks/degraded-performance.md`
- Benchmark regression: `docs/runbooks/performance-regression.md`

## Global Response Expectations

1. Capture the exact failure signal first (error output, timestamps, command).
2. Prefer reversible mitigation steps before code/config changes.
3. Record every action taken with UTC timestamps in the incident note.
4. Use rollback sections in each runbook when a mitigation worsens behavior.
