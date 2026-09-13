# Runbook: API Quota or Rate Limit Incident

## Scope

Use this runbook when routing requests fail due to Google Maps quota exhaustion
or HTTP rate-limit/server pressure responses.

## Symptoms

- Errors mention `429`, `OVER_QUERY_LIMIT`, or quota exceeded.
- Repeated retries with eventual failure.
- Routing requests degrade across all users/sessions.

## Immediate Triage

1. Confirm error class and status:
   - Run affected flow with `FASTEST_ROUTE_LOG_LEVEL=DEBUG`.
2. Verify API key loaded at runtime:
   - `PYTHONPATH=TSP_GOOGLE_MAPS ./.venv/bin/python -c "from fastest_route.config.loader import load_config; print(bool(load_config().google_maps.api_key))"`
3. Confirm retry/rate-limit configuration:
   - Review `[http]` and `[rate_limit]` in `TSP_GOOGLE_MAPS/config.toml`.

## Debugging Steps

1. Identify response distribution:
   - Search logs for 429/5xx concentration and request burst patterns.
2. Validate backoff and retry limits:
   - Check `retry_max_attempts`, `retry_base_delay_seconds`, and `retry_jitter_ratio`.
3. Validate rate limiter behavior:
   - Check `requests_per_second`, `burst`, and `max_wait_seconds`.
4. Confirm external quota state in cloud console:
   - Verify project-level usage and quota ceilings for Distance Matrix/Geocoding.

## Mitigations

1. Reduce request pressure quickly:
   - Lower `rate_limit.requests_per_second`.
   - Lower `rate_limit.burst`.
2. Avoid retry storms:
   - Reduce `http.retry_max_attempts` temporarily if upstream is hard-failing.
3. Increase cache effectiveness:
   - Confirm disk cache paths are writable and cache TTL is not overly low.
4. If quota exhausted, rotate to approved backup key/project per team policy.

## Rollback Procedure

Use rollback when mitigations over-throttle the app or increase failure rate.

1. Restore previous known-good `TSP_GOOGLE_MAPS/config.toml`.
2. Re-run verification:
   - `make check`
3. Execute a known-good route request and confirm normal latency/error profile.
4. Revert emergency key/project changes after quota recovery window ends.

## Exit Criteria

- 429/quota errors are within acceptable threshold.
- Routing success rate returns to normal baseline.
- Temporary throttle changes are either documented as permanent or reverted.
