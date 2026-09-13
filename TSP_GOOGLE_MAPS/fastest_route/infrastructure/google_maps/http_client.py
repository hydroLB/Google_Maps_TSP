"""HTTP helper for Google Maps clients with retries, rate limiting, and JSON parsing."""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING

import requests

from fastest_route.shared.errors import (
    DeadlineExceededError,
    ExternalServiceError,
    RateLimitError,
    RetryableExternalServiceError,
    ValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastest_route.infrastructure.rate_limit import RateLimiter
    from fastest_route.infrastructure.retry import RetryPolicy
    from fastest_route.shared.cancellation import CancellationToken

_PERMANENT_REQUEST_EXCEPTIONS = (
    requests.exceptions.InvalidHeader,
    requests.exceptions.InvalidSchema,
    requests.exceptions.InvalidURL,
    requests.exceptions.MissingSchema,
    requests.exceptions.TooManyRedirects,
    requests.exceptions.URLRequired,
)


class GoogleMapsHttpClient:
    """Execute HTTP GET requests with JSON parsing, retries, and rate limiting."""

    def __init__(
        self,
        *,
        session_provider: Callable[[], requests.Session],
        timeout_seconds: float,
        rate_limiter: RateLimiter,
        retry_policy: RetryPolicy,
        retry_statuses: Sequence[int],
    ) -> None:
        location = (
            "fastest_route.infrastructure.google_maps.http_client.GoogleMapsHttpClient.__init__"
        )
        if not isinstance(timeout_seconds, int | float) or timeout_seconds <= 0:
            raise ValidationError(location, "timeout_seconds must be positive.")
        if not callable(session_provider):
            raise ValidationError(location, "session_provider must be callable.")
        self._session_provider = session_provider
        self._timeout_seconds = float(timeout_seconds)
        self._rate_limiter = rate_limiter
        self._retry_policy = retry_policy
        self._retry_statuses = tuple(int(code) for code in retry_statuses)

    def get_json(
        self,
        url: str,
        params: Mapping[str, str],
        *,
        location: str,
        cancellation_token: CancellationToken | None = None,
        deadline: float | None = None,
    ) -> Mapping[str, object]:
        """Perform a GET request and parse a JSON mapping response."""
        method_location = (
            "fastest_route.infrastructure.google_maps.http_client.GoogleMapsHttpClient.get_json"
        )
        if not isinstance(url, str) or not url.strip():
            raise ValidationError(method_location, "url must be a non empty string.")
        if not isinstance(location, str) or not location.strip():
            raise ValidationError(method_location, "location must be a non empty string.")

        def ensure_active() -> None:
            if cancellation_token is not None:
                cancellation_token.raise_if_cancelled(location)
            if deadline is not None and time.monotonic() >= deadline:
                raise DeadlineExceededError(location, "Operation deadline exceeded.")

        def perform_request() -> Mapping[str, object]:
            """Run the single request attempt passed to the retry policy."""
            ensure_active()
            try:
                self._rate_limiter.acquire(
                    cancellation_token=cancellation_token,
                    deadline=deadline,
                )
            except RateLimitError as exc:
                raise RetryableExternalServiceError(location, "Rate limit exceeded.") from exc
            ensure_active()
            request_timeout = self._timeout_seconds
            if deadline is not None:
                request_timeout = min(request_timeout, deadline - time.monotonic())
                if request_timeout <= 0:
                    raise DeadlineExceededError(location, "Operation deadline exceeded.")
            try:
                session = self._session_provider()
                response = session.get(
                    url,
                    params=params,
                    timeout=request_timeout,
                )
            except requests.RequestException as exc:
                ensure_active()
                if isinstance(exc, _PERMANENT_REQUEST_EXCEPTIONS):
                    raise ExternalServiceError(
                        location, "HTTP request configuration was invalid."
                    ) from exc
                raise RetryableExternalServiceError(location, "HTTP request failed.") from exc
            ensure_active()
            if response.status_code in self._retry_statuses:
                raise RetryableExternalServiceError(
                    location, f"Retryable HTTP status {response.status_code}."
                )
            if response.status_code != 200:
                raise ExternalServiceError(
                    location, f"Unexpected HTTP status {response.status_code}."
                )
            try:
                payload = json.loads(response.text)
            except json.JSONDecodeError as exc:
                raise ExternalServiceError(location, "Response JSON parsing failed.") from exc
            ensure_active()
            if not isinstance(payload, Mapping):
                raise ExternalServiceError(location, "Response JSON was not a mapping.")
            return payload

        return self._retry_policy.execute(
            perform_request,
            location=location,
            cancellation_token=cancellation_token,
            deadline=deadline,
        )
