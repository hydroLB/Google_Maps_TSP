# ADR 0003: Batch Matrix Requests and Classify Retryable Failures

## Status

Accepted

## Date

2026-07-10

## Context

Route optimization needs every directed cost between the selected locations. Issuing one
Distance Matrix request per leg repeats connection and rate-limit overhead, consumes quota less
efficiently, and lengthens the period in which a user can cancel. The provider also reports both
transient and permanent failures through HTTP status codes and JSON response statuses. Retrying
every integration error wastes quota and makes invalid requests slow to fail.

The current desktop input limits produce at most 81 matrix elements, below the legacy endpoint's
100-element request bound.

## Decision

- Request the complete supported square matrix in one bounded provider call when the per-leg
  cache cannot satisfy the entire matrix.
- Validate the response dimensions and every directed element before exposing the matrix to the
  solver or writing its legs to the cache.
- Treat transport failures, configured retryable HTTP statuses, `OVER_QUERY_LIMIT`, and
  `UNKNOWN_ERROR` as retryable integration failures.
- Surface invalid payloads, denied requests, and other permanent failures immediately.
- Bucket `departure_time=now` cache identities into five-minute windows so live-traffic values do
  not become indefinitely reusable. Bucket rotation prevents a superseded entry from being read
  for a new request; it does not delete old entries, which remain until the configured TTL expires.
- Keep the behavior behind the existing route-matrix port so migration to Routes API Compute
  Route Matrix remains an adapter change.

## Consequences

Positive:

- A cold route matrix uses one provider round trip instead of one per directed leg.
- Retry delays and quota consumption are limited to failures that may succeed later.
- Strict response-shape validation prevents a partial provider response from reaching the solver.
- Cache behavior remains deterministic and directly testable.

Negative:

- One missing cached leg triggers a complete matrix fetch because the legacy API cannot express an
  arbitrary sparse set of origin/destination pairs without returning unwanted cross-products.
- The batching bound must be revisited if product input limits grow.
- Traffic-aware buckets can coexist on disk until TTL cleanup, so rotation is freshness isolation,
  not an immediate storage-reclamation policy.
- The legacy adapters and provider-content retention policy remain migration concerns documented
  in the README roadmap.

## Alternatives Considered

1. Continue making one request per directed leg. Rejected because it scales external IO
   quadratically and adds avoidable quota, latency, and retry overhead.
2. Retry every `ExternalServiceError`. Rejected because authentication, malformed requests, and
   invalid responses are not expected to improve on another attempt.
3. Cache live-traffic results under the literal value `now`. Rejected because it gives moving
   traffic data an identity that never changes before TTL expiry.
