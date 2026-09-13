# Error Model

## Taxonomy

Boundary-facing failures use a stable code taxonomy from
`fastest_route.shared.errors.ErrorCode`:

- `E_CONFIG`
- `E_VALIDATION`
- `E_CACHE`
- `E_EXTERNAL_IO`
- `E_RATE_LIMIT`
- `E_CANCELLED`
- `E_INTERNAL`

`RetryableExternalServiceError` remains in the `E_EXTERNAL_IO` category while carrying an
internal retryability signal. Permanent provider failures use `ExternalServiceError` directly and
surface after one attempt.

`DeadlineExceededError` also maps to `E_EXTERNAL_IO`. Matrix operations propagate one absolute
deadline through rate limiting, retry backoff, and per-attempt HTTP timeout selection so nested
policies cannot restart the caller's time budget.

## Boundary Mapping

Boundary handlers should use:

- `error_code_for_exception(exc)` for structured logging dimensions
- `format_boundary_error_message(exc)` for user-facing and ops-facing messages

Current boundary integrations:

- UI worker/job boundary:
  `fastest_route.presentation.gui.app.controllers.routing_controller.RoutingController._compute_route_worker`
- App entrypoint boundary:
  `fastest_route.entrypoint.main`
- External IO boundary:
  `fastest_route.infrastructure.google_maps.client.GoogleMapsClient._request_json`

This keeps user-visible errors and operational logs consistent without changing core behavior.
