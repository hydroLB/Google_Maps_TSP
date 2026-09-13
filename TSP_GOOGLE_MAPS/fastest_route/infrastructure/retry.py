"""Retry policy with exponential backoff and jitter.

Makes retry behavior explicit and consistent."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from fastest_route.shared.errors import (
    AppError,
    DeadlineExceededError,
    ExternalServiceError,
    RetryableExternalServiceError,
    ValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fastest_route.shared.cancellation import CancellationToken

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Configure retry behavior with exponential backoff and jitter.

    Makes retry behavior explicit and configurable."""

    max_attempts: int
    base_delay_seconds: float
    max_delay_seconds: float
    jitter_ratio: float
    retry_statuses: Sequence[int]

    def next_delay(self, attempt: int) -> float:
        """Compute the next backoff delay for a retry attempt.

        Keeps retry delay math centralized and testable."""
        location = "fastest_route.infrastructure.retry.RetryPolicy.next_delay"
        if attempt <= 0:
            raise ValidationError(location, "attempt must be positive.")
        try:
            exponential = self.base_delay_seconds * (2 ** max(attempt - 1, 0))
            clamped = min(exponential, self.max_delay_seconds)
            jitter = 0.0
            if self.jitter_ratio:
                jitter_fraction = secrets.randbelow(1_000_000) / 1_000_000.0
                jitter = clamped * self.jitter_ratio * jitter_fraction
            return float(min(clamped + jitter, self.max_delay_seconds))
        except (TypeError, ValueError) as exc:
            raise ValidationError(location, "Failed to compute retry delay.") from exc

    def execute(
        self,
        operation: Callable[[], T],
        *,
        location: str,
        cancellation_token: CancellationToken | None = None,
        deadline: float | None = None,
    ) -> T:
        """Execute an operation with retry behavior.

        Centralizes retry loops so callers do not reimplement backoff and jitter."""
        last_error: Exception | None = None
        if not callable(operation):
            raise ExternalServiceError(location, "operation must be callable.")
        try:
            for attempt in range(1, self.max_attempts + 1):
                if cancellation_token is not None:
                    cancellation_token.raise_if_cancelled(location)
                self._raise_if_deadline_exceeded(deadline=deadline, location=location)
                try:
                    result = operation()
                    self._raise_if_deadline_exceeded(deadline=deadline, location=location)
                    return result
                except RetryableExternalServiceError as exc:
                    last_error = exc
                    self._raise_if_deadline_exceeded(deadline=deadline, location=location)
                    if attempt >= self.max_attempts:
                        break
                    delay = self.next_delay(attempt)
                    if delay > 0:
                        if deadline is not None and delay >= deadline - time.monotonic():
                            raise DeadlineExceededError(
                                location, "Operation deadline exceeded."
                            ) from exc
                        self._sleep(
                            delay,
                            cancellation_token=cancellation_token,
                            location=location,
                            deadline=deadline,
                        )
                except ExternalServiceError:
                    raise
        except ValidationError as exc:
            raise ExternalServiceError(location, f"Retry calculation failed. {exc}") from exc
        except AppError:
            raise
        except (RuntimeError, TypeError) as exc:
            raise ExternalServiceError(location, "Retry execution failed.") from exc
        message = "Retry attempts exhausted."
        if last_error:
            raise ExternalServiceError(location, message) from last_error
        raise ExternalServiceError(location, message)

    def _sleep(
        self,
        seconds: float,
        *,
        cancellation_token: CancellationToken | None,
        location: str,
        deadline: float | None = None,
    ) -> None:
        """Sleep for a bounded time while honoring cancellation requests.

        Ensures retry backoff does not block shutdown or user cancel actions."""
        if seconds <= 0:
            return
        sleep_deadline = time.monotonic() + seconds
        while True:
            if cancellation_token is not None:
                cancellation_token.raise_if_cancelled(location)
            self._raise_if_deadline_exceeded(deadline=deadline, location=location)
            now = time.monotonic()
            remaining = sleep_deadline - now
            if remaining <= 0:
                return
            if deadline is not None:
                remaining = min(remaining, deadline - now)
            time.sleep(min(remaining, 0.05))

    @staticmethod
    def _raise_if_deadline_exceeded(*, deadline: float | None, location: str) -> None:
        if deadline is not None and time.monotonic() >= deadline:
            raise DeadlineExceededError(location, "Operation deadline exceeded.")
