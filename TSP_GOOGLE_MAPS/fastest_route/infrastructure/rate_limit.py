"""Token bucket rate limiter for outbound requests."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from fastest_route.shared.errors import AppError, DeadlineExceededError, RateLimitError

if TYPE_CHECKING:
    from fastest_route.shared.cancellation import CancellationToken


class RateLimiter:
    """Enforce a token bucket rate limit for outbound requests."""

    def __init__(self, rate_per_second: float, burst: int, max_wait_seconds: float) -> None:
        location = "fastest_route.infrastructure.rate_limit.RateLimiter.__init__"
        if rate_per_second <= 0:
            raise RateLimitError(location, "rate_per_second must be positive.")
        if burst <= 0:
            raise RateLimitError(location, "burst must be positive.")
        if max_wait_seconds <= 0:
            raise RateLimitError(location, "max_wait_seconds must be positive.")
        try:
            self._rate = rate_per_second
            self._capacity = float(burst)
            self._tokens = float(burst)
            self._lock = threading.Lock()
            self._last_refill = time.monotonic()
            self._max_wait = max_wait_seconds
        except RuntimeError as exc:
            raise RateLimitError(location, "Failed to initialize rate limiter.") from exc

    def acquire(
        self,
        *,
        cancellation_token: CancellationToken | None = None,
        deadline: float | None = None,
    ) -> None:
        """Acquire a token, waiting if necessary within the max wait limit."""
        location = "fastest_route.infrastructure.rate_limit.RateLimiter.acquire"
        try:
            limiter_deadline = time.monotonic() + self._max_wait
            while True:
                if cancellation_token is not None:
                    cancellation_token.raise_if_cancelled(location)
                now = time.monotonic()
                if deadline is not None and now >= deadline:
                    raise DeadlineExceededError(location, "Operation deadline exceeded.")
                with self._lock:
                    elapsed = now - self._last_refill
                    if elapsed > 0:
                        refill = elapsed * self._rate
                        self._tokens = min(self._capacity, self._tokens + refill)
                        self._last_refill = now
                    if self._tokens >= 1:
                        self._tokens -= 1
                        return
                    seconds_until_token = max((1.0 - self._tokens) / self._rate, 0.0)
                now = time.monotonic()
                if deadline is not None and now >= deadline:
                    raise DeadlineExceededError(location, "Operation deadline exceeded.")
                limiter_remaining = limiter_deadline - now
                if limiter_remaining <= 0:
                    raise RateLimitError(location, "Rate limit wait time exceeded.")
                operation_remaining = deadline - now if deadline is not None else limiter_remaining
                time.sleep(min(seconds_until_token, limiter_remaining, operation_remaining, 0.05))
        except RateLimitError:
            raise
        except AppError:
            raise
        except RuntimeError as exc:
            raise RateLimitError(location, "Failed to acquire rate limit token.") from exc
