from __future__ import annotations

import time

import pytest

from fastest_route.infrastructure.rate_limit import RateLimiter
from fastest_route.infrastructure.retry import RetryPolicy
from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import (
    CancellationError,
    DeadlineExceededError,
    ExternalServiceError,
    RateLimitError,
    RetryableExternalServiceError,
    ValidationError,
)


def test_rate_limiter_rejects_expired_operation_deadline() -> None:
    limiter = RateLimiter(rate_per_second=1.0, burst=1, max_wait_seconds=10.0)

    with pytest.raises(DeadlineExceededError):
        limiter.acquire(deadline=time.monotonic() - 1.0)


def test_retry_policy_does_not_start_retry_beyond_deadline() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        base_delay_seconds=1.0,
        max_delay_seconds=1.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )
    attempts = 0

    def operation() -> int:
        nonlocal attempts
        attempts += 1
        raise RetryableExternalServiceError("test", "temporary")

    with pytest.raises(DeadlineExceededError):
        policy.execute(
            operation,
            location="test",
            deadline=time.monotonic() + 0.01,
        )

    assert attempts == 1


def test_rate_limiter_acquire_allows_fast_path() -> None:
    limiter = RateLimiter(rate_per_second=1000.0, burst=2, max_wait_seconds=1.0)
    limiter.acquire()
    limiter.acquire()


def test_rate_limiter_raises_when_wait_exceeded() -> None:
    limiter = RateLimiter(rate_per_second=0.1, burst=1, max_wait_seconds=0.01)
    limiter.acquire()
    with pytest.raises(RateLimitError):
        limiter.acquire()


def test_rate_limiter_respects_cancellation() -> None:
    limiter = RateLimiter(rate_per_second=0.1, burst=1, max_wait_seconds=10.0)
    limiter.acquire()
    token = CancellationToken()
    token.cancel()
    with pytest.raises(CancellationError):
        limiter.acquire(cancellation_token=token)


def test_rate_limiter_invalid_config_raises() -> None:
    with pytest.raises(RateLimitError):
        RateLimiter(rate_per_second=0.0, burst=1, max_wait_seconds=1.0)
    with pytest.raises(RateLimitError):
        RateLimiter(rate_per_second=1.0, burst=0, max_wait_seconds=1.0)
    with pytest.raises(RateLimitError):
        RateLimiter(rate_per_second=1.0, burst=1, max_wait_seconds=0.0)


def test_retry_policy_retries_then_succeeds() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )
    attempts = {"count": 0}

    def operation() -> int:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RetryableExternalServiceError("test", "boom")
        return 42

    result = policy.execute(operation, location="test")
    assert result == 42
    assert attempts["count"] == 2


def test_retry_policy_raises_after_exhaustion() -> None:
    policy = RetryPolicy(
        max_attempts=2,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )

    def operation() -> int:
        raise RetryableExternalServiceError("test", "boom")

    with pytest.raises(ExternalServiceError):
        policy.execute(operation, location="test")


def test_retry_policy_respects_cancellation() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        base_delay_seconds=1.0,
        max_delay_seconds=1.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )
    token = CancellationToken()
    attempts = {"count": 0}

    def operation() -> int:
        attempts["count"] += 1
        if attempts["count"] == 1:
            token.cancel()
        raise RetryableExternalServiceError("test", "boom")

    with pytest.raises(CancellationError):
        policy.execute(operation, location="test", cancellation_token=token)
    assert attempts["count"] == 1


def test_retry_policy_does_not_repeat_permanent_failures() -> None:
    """Permanent provider failures must surface after exactly one attempt."""

    policy = RetryPolicy(
        max_attempts=3,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )
    attempts = 0

    def operation() -> int:
        nonlocal attempts
        attempts += 1
        raise ExternalServiceError("test", "request denied")

    with pytest.raises(ExternalServiceError):
        policy.execute(operation, location="test")
    assert attempts == 1


def test_retry_policy_delay_calculation() -> None:
    policy = RetryPolicy(
        max_attempts=1,
        base_delay_seconds=0.5,
        max_delay_seconds=1.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )
    assert policy.next_delay(1) == 0.5


def test_retry_policy_delay_applies_positive_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive jitter still increases delays that remain below the configured cap."""
    policy = RetryPolicy(
        max_attempts=1,
        base_delay_seconds=0.5,
        max_delay_seconds=2.0,
        jitter_ratio=0.2,
        retry_statuses=(500,),
    )
    monkeypatch.setattr(
        "fastest_route.infrastructure.retry.secrets.randbelow",
        lambda upper_bound: upper_bound // 2,
    )

    assert policy.next_delay(1) == pytest.approx(0.55)


def test_retry_policy_delay_caps_maximum_positive_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured max delay remains an upper bound after jitter is added."""
    policy = RetryPolicy(
        max_attempts=1,
        base_delay_seconds=0.75,
        max_delay_seconds=1.0,
        jitter_ratio=0.5,
        retry_statuses=(500,),
    )
    monkeypatch.setattr(
        "fastest_route.infrastructure.retry.secrets.randbelow",
        lambda upper_bound: upper_bound - 1,
    )

    assert policy.next_delay(1) == policy.max_delay_seconds


def test_retry_policy_delay_rejects_invalid_attempt() -> None:
    policy = RetryPolicy(
        max_attempts=1,
        base_delay_seconds=0.1,
        max_delay_seconds=1.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )
    with pytest.raises(ValidationError):
        policy.next_delay(0)


def test_retry_policy_execute_requires_callable() -> None:
    policy = RetryPolicy(
        max_attempts=1,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
        jitter_ratio=0.0,
        retry_statuses=(500,),
    )
    with pytest.raises(ExternalServiceError):
        policy.execute(None, location="test")
