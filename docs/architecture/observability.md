# Observability Model

## Structured Log Schema

All logs emitted through `fastest_route.observability.logger.StructuredFormatter` follow a
stable JSON schema:

- `schema_version`
- `service`
- `timestamp`
- `level`
- `logger`
- `event`
- `message`
- `correlation_id`
- `component`
- `fields` (always present as an object, may be empty)
- `error_code` (optional, top-level when provided)
- `exception` (optional)

Current schema constants:

- `LOG_SCHEMA_VERSION = "1.0"`
- `LOG_SERVICE_NAME = "fastest_route_optimizer"`

## Correlation ID Propagation

Correlation IDs are context-managed in `fastest_route.observability.context`:

- `correlation_context(...)` scopes request/job tracing.
- `StructuredAdapter.process(...)` injects `correlation_id` on every log call.
- `StructuredFormatter` includes it in every emitted log payload.

Verification coverage:

- `tests/unit/test_observability.py::test_correlation_id_propagates_across_logger_adapters`
- `tests/unit/test_observability.py::test_structured_formatter_includes_correlation_id`

## Redaction Guarantees

Redaction is centrally applied in `fastest_route.observability.logger._redact_fields` and
`_scrub_inline_secrets`:

- Secret-like fields (`api_key`, `token`, `authorization`, etc.) are masked.
- PII-like fields (`origin`, `destination`, `address`, etc.) become keyed,
  process-scoped tokens for correlation within one run. The tokens are intentionally not
  stable across restarts and cannot be reproduced from an address alone.
- Inline secret patterns in strings (for example query params and bearer tokens) are scrubbed.

Verification coverage:

- `tests/unit/test_observability.py::test_structured_formatter_emits_fields_and_redacts_extras`
- `tests/unit/test_observability.py::test_structured_formatter_scrubs_inline_secrets_from_message`

## Metrics Hook Path

Basic metrics hooks are available without external dependencies via
`fastest_route.observability.metrics`:

- `increment_counter(name, value=1, tags=None)`
- `observe_duration_seconds(name, value, tags=None)`
- `set_metric_sink(...)` / `reset_metric_sink()` for optional runtime wiring

Current instrumentation code path:

- `fastest_route.presentation.gui.app.controllers.routing_job.compute_route_artifacts`
  emits:
  - `routing.requests_total`
  - `routing.success_total` / `routing.failure_total`
  - `routing.compute_duration_seconds`

Verification coverage:

- `tests/unit/test_metrics_hooks.py`
