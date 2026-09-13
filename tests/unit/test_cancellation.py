from __future__ import annotations

import pytest

from fastest_route.shared.cancellation import CancellationToken
from fastest_route.shared.errors import CancellationError


def test_cancellation_token_flags_cancelled() -> None:
    token = CancellationToken()
    assert not token.is_cancelled()
    token.cancel()
    assert token.is_cancelled()


def test_cancellation_token_raises() -> None:
    token = CancellationToken()
    token.cancel()
    with pytest.raises(CancellationError):
        token.raise_if_cancelled("test")


def test_cancellation_token_cancel_error() -> None:
    token = CancellationToken()

    class BadEvent:
        def set(self) -> None:
            raise RuntimeError("boom")

    token._event = BadEvent()
    with pytest.raises(CancellationError):
        token.cancel()


def test_cancellation_token_is_cancelled_error() -> None:
    token = CancellationToken()

    class BadEvent:
        def is_set(self) -> bool:
            raise RuntimeError("boom")

    token._event = BadEvent()
    with pytest.raises(CancellationError):
        token.is_cancelled()


def test_cancellation_token_raise_if_cancelled_error() -> None:
    token = CancellationToken()

    class BadEvent:
        def is_set(self) -> bool:
            raise RuntimeError("boom")

    token._event = BadEvent()
    with pytest.raises(CancellationError):
        token.raise_if_cancelled("test")
