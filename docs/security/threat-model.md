# Threat Model Notes

## Scope

This document captures lightweight threat model notes for key entry surfaces:

- API key input and storage path.
- Outbound Google Maps API calls.
- Local file and cache writes.
- User-selected CSV route exports.

## Trust Boundaries

1. User input boundary:
   - GUI fields and startup dialogs.
2. External network boundary:
   - Outbound HTTP to Google Maps APIs.
3. Local filesystem boundary:
   - Config, plaintext credential, cache, and exported CSV files.

## Surface: API Key Input

Entry points:

- Stable `.env` credential file / process environment variable `GOOGLE_MAPS_API_KEY`.
- Runtime key input dialog in GUI startup flow.

Primary threats:

- Secret leakage in logs.
- Accidental commit of secrets to git.
- Invalid or maliciously malformed key values causing ambiguous failures.

Current mitigations:

- Structured log redaction in `fastest_route.observability.logger`.
- `.env.example` is checked in; source and user-config `.env` files are excluded from the repo.
- Source launches use the repository-root `.env`. Installed entry points use
  `$XDG_CONFIG_HOME/fastest_route/.env` or `~/.config/fastest_route/.env`, independent of the
  current working directory.
- `.env` loading accepts only the API key, environment label, and log level. It ignores
  proxy/certificate variables and the config-path override, preventing credential-file contents
  from redirecting provider requests.
- GUI credential persistence uses atomic replacement and user-only permissions on POSIX systems.
- Config validation and fail-fast startup guarantees.
- Secret scan in CI via gitleaks and dependency/security checks in `make check`.

Residual risks:

- `.env` deliberately stores the API key as plaintext. A compromised account, backup, or process
  with access to the user's files can expose it even when file permissions are restrictive.
- Secrets pasted into non-redacted channels outside app logs.

Recommended operator actions:

- Use scoped API keys with provider-side quota and restrictions.
- Rotate keys on suspected exposure.
- Run local `gitleaks detect --source . --config gitleaks.toml --redact` before push.

## Surface: Outbound API Calls

Entry points:

- Google Maps client and HTTP client stack under `fastest_route.infrastructure.google_maps`.

Primary threats:

- Denial of service via upstream slowness or throttling.
- Untrusted response content causing parser errors.
- Information leakage through URL/query logging.

Current mitigations:

- Explicit timeout, retry, and backoff controls in `[http]` config.
- Rate limiter controls in `[rate_limit]` config.
- A single matrix deadline caps rate-limit waits, retry backoff, and each request timeout.
- Error mapping at boundaries with structured logs.
- Redaction/scrubbing for secret-like values in logging path.
- Provider endpoint configuration is restricted to HTTPS on `maps.googleapis.com`, limiting a
  config-path override from forwarding the API key to an arbitrary host.

Residual risks:

- Upstream outage still impacts availability.
- Misconfigured retry/rate settings can amplify latency.
- The synchronous `requests` transport cannot interrupt an active socket call on user
  cancellation; its timeout is an inactivity bound rather than a real-time scheduler guarantee.

Recommended operator actions:

- Keep retries bounded and jitter enabled.
- Monitor quota and 429/5xx patterns.
- Tune `rate_limit` and cache settings during incidents using runbooks.

## Surface: Local File and Cache Writes

Entry points:

- Distance and geocode cache disk paths.
- Runtime config file path override (`FASTEST_ROUTE_CONFIG_PATH`).
- CSV paths chosen by the user through the export dialog.

Primary threats:

- Path misuse leading to writes in unsafe directories.
- Corrupted cache files affecting runtime behavior.
- Sensitive data persistence beyond desired retention.

Current mitigations:

- Centralized config validation for cache paths and TTL settings.
- Deterministic loader behavior and startup validation.
- SHA-256 distance-cache keys prevent plaintext addresses from appearing in cache keys.
- Cache files are replaced atomically and written with user-only permissions on POSIX systems.
- Incident runbooks for config and degraded performance failures.

Residual risks:

- Optional disk geocode entries can include plaintext input and formatted addresses. Distance
  cache keys are hashed, but their values remain provider-derived content.
- Traffic-aware cache identities rotate every five minutes, but superseded buckets remain until
  their TTL expires.
- Provider terms restrict both memory and disk content use independently of local filesystem
  security. The repository has not completed the provider-specific compliance review needed for
  production distribution.

Recommended operator actions:

- Use user-private filesystem paths with least privilege permissions.
- Periodically clear cache files in sensitive environments.
- Disable provider-content persistence for production distribution unless the applicable provider
  agreement explicitly permits the chosen retention behavior.
- Include cache path review in environment hardening checklists.

## Surface: CSV Route Exports

Entry point:

- User-selected destination in the GUI's **Export CSV** flow.

Primary threats:

- Full origin, destination, and stop addresses disclose sensitive location history.
- Exporting to a synchronized, shared, or world-readable directory broadens access.

Current mitigations:

- The user explicitly selects the output path; the app does not upload the CSV.
- Export errors are surfaced without logging file contents or API credentials.

Residual risks and operator actions:

- CSV is plaintext and has no application-level encryption or retention control.
- Store exports only in an appropriately protected location and delete them when no longer needed.

## Production Compliance Boundary

The application currently depends on legacy Google Maps APIs and caches provider-derived data.
Provider caching/retention compliance is unresolved for public distribution. The repository also
does not ship publicly accessible, provider-compliant terms of use or a privacy policy. These are
release blockers, not protections supplied by the current desktop build.
