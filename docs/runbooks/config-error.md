# Runbook: Configuration Error

## Scope

Use this runbook when startup or runtime fails due to invalid configuration
values, missing required settings, or invalid environment overrides.

## Symptoms

- Startup exits with `ConfigError` or `ValidationError` from config modules.
- Runtime behavior is inconsistent with expected defaults.
- Environment-specific failures appear after config edits.

## Immediate Triage

1. Confirm active environment variables:
   - `env | rg '^FASTEST_ROUTE_|^GOOGLE_MAPS_API_KEY'`
2. Validate config load directly:
   - `PYTHONPATH=TSP_GOOGLE_MAPS ./.venv/bin/python -m fastest_route --check-config`
3. Compare against reference:
   - `docs/config/reference.md`

## Debugging Steps

1. Identify failing section from stack trace boundary:
   - `fastest_route.config.loading.sections.*`
   - `fastest_route.config.schema.*`
2. Validate constraints for reported key:
   - Type, min/max bounds, enum domain, and required fields.
3. Check environment layering precedence:
   - Env overrides > config file > loader defaults.
4. Detect empty-string env override problems:
   - Ensure required values are not set to whitespace-only strings.

## Mitigations

1. Restore section-level defaults in `TSP_GOOGLE_MAPS/config.toml`.
2. Remove invalid env override or set valid value.
3. Re-run deterministic validation:
   - `make check`
4. If API key is missing in non-dev environment, provide valid key and rerun.

## Rollback Procedure

Use rollback when attempted config fixes introduce broader failures.

1. Revert config file to last known-good revision:
   - `git checkout <known_good_commit> -- TSP_GOOGLE_MAPS/config.toml`
2. Clear override variables and shell state:
   - `unset FASTEST_ROUTE_CONFIG_PATH FASTEST_ROUTE_ENV FASTEST_ROUTE_LOG_LEVEL GOOGLE_MAPS_API_KEY`
3. Re-apply only minimal required settings.
4. Validate with:
   - `make check`

## Exit Criteria

- Config loads successfully via direct loader call.
- `make dev` and `make check` both pass.
- Root cause and final validated config values are documented.
