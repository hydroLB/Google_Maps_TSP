"""Correlation id context helpers for structured logging."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING
from uuid import uuid4

from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Iterator

CORRELATION_ID: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_correlation_id() -> str:
    """Generate a new correlation identifier for a request flow."""
    location = "fastest_route.observability.context.generate_correlation_id"
    try:
        return uuid4().hex
    except RuntimeError as exc:
        raise ValidationError(location, "Failed to generate correlation id.") from exc


def get_correlation_id() -> str:
    """Fetch the current correlation id from context."""
    location = "fastest_route.observability.context.get_correlation_id"
    try:
        return CORRELATION_ID.get()
    except LookupError as exc:
        raise ValidationError(location, "Correlation id lookup failed.") from exc


def set_correlation_id(correlation_id: str) -> None:
    """Set the current correlation id in context."""
    location = "fastest_route.observability.context.set_correlation_id"
    if not isinstance(correlation_id, str):
        raise ValidationError(location, "correlation_id must be a string.")
    try:
        CORRELATION_ID.set(correlation_id)
    except RuntimeError as exc:
        raise ValidationError(location, "Failed to set correlation id.") from exc


@contextmanager
def correlation_context(correlation_id: str | None = None) -> Iterator[None]:
    """Provide a context manager for scoped correlation id usage."""
    location = "fastest_route.observability.context.correlation_context"
    if correlation_id is not None and not isinstance(correlation_id, str):
        raise ValidationError(location, "correlation_id must be a string when provided.")
    token = CORRELATION_ID.set(correlation_id or generate_correlation_id())
    try:
        yield
    finally:
        try:
            CORRELATION_ID.reset(token)
        except RuntimeError as exc:
            raise ValidationError(location, "Failed to reset correlation id.") from exc
