# Runbook: Degraded Performance

## Scope

Use this runbook when route computation latency or UI responsiveness regresses
without complete service failure.

## Symptoms

- Route generation is significantly slower than baseline.
- UI appears blocked during optimization flow.
- Controlled same-host benchmark measurements report a regression.

## Immediate Triage

1. Capture a benchmark measurement:
   - `make bench`
2. Capture current hot path profile:
   - `make profile`
3. Check for elevated retry activity or rate-limit waiting in logs.

## Debugging Steps

1. Identify latency source:
   - Network/API latency.
   - Cache miss amplification.
   - Solver compute expansion.
2. Review critical tunables:
   - `[http].timeout_seconds`, `retry_*`
   - `[rate_limit].requests_per_second`, `burst`, `max_wait_seconds`
   - `[routing].max_exact`, `two_opt_max_passes`
3. Check cache behavior:
   - Verify disk path writable and cache TTL settings are sane.
4. Compare against baseline code path:
   - Confirm no accidental debug logging or excessive retries were introduced.

## Mitigations

1. Reduce compute-heavy settings temporarily:
   - Lower `routing.max_exact` and/or `routing.two_opt_max_passes`.
2. Reduce retry overhead during upstream instability:
   - Lower `http.retry_max_attempts`.
3. Improve cache hit rate:
   - Increase cache size limits where memory budget allows.
4. Re-run `make bench` under the same host and load conditions after each change.

## Rollback Procedure

Use rollback when mitigation reduces route quality too far or fails to improve latency.

1. Revert performance-related config changes to known-good values.
2. If regression is code-induced, return to last known-good commit for affected module.
3. Confirm recovery:
   - `make bench`
   - `make check`
4. Record regression signature and open follow-up optimization issue with profile output.

## Exit Criteria

- Repeated same-host measurements show the expected recovery.
- Interactive route flow meets expected response envelope.
- Any temporary config degradations are reverted or explicitly accepted.
