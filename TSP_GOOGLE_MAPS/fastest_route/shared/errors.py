"""Shared error types for consistent, location tagged failures."""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Stable error taxonomy used by boundary handlers for logging and UI messaging."""

    CONFIG = "E_CONFIG"
    VALIDATION = "E_VALIDATION"
    CACHE = "E_CACHE"
    EXTERNAL_IO = "E_EXTERNAL_IO"
    RATE_LIMIT = "E_RATE_LIMIT"
    CANCELLED = "E_CANCELLED"
    INTERNAL = "E_INTERNAL"


class AppError(RuntimeError):
    """Base error that includes a location prefix in the message."""

    default_code = ErrorCode.INTERNAL

    def __init__(self, location: str, message: str, *, code: ErrorCode | None = None) -> None:
        self.location = location
        self.message = message
        self.code = code or self.default_code
        super().__init__(f"{location}: {message}")


class ConfigError(AppError):
    """Configuration validation or load failure."""

    default_code = ErrorCode.CONFIG


class ValidationError(AppError):
    """Invalid input or domain validation failure."""

    default_code = ErrorCode.VALIDATION


class CacheError(AppError):
    """Cache load or save failure with context."""

    default_code = ErrorCode.CACHE


class ExternalServiceError(AppError):
    """External service failure such as Google Maps API errors."""

    default_code = ErrorCode.EXTERNAL_IO


class RetryableExternalServiceError(ExternalServiceError):
    """A transient external failure that is safe to retry.

    Keeping retryability in the error type prevents permanent failures such as malformed
    responses, denied credentials, and non-retryable HTTP statuses from being repeated.
    """


class DeadlineExceededError(ExternalServiceError):
    """An external operation exhausted its caller-provided wall-clock budget."""


class RateLimitError(AppError):
    """Rate limiting failure for API calls."""

    default_code = ErrorCode.RATE_LIMIT


class CancellationError(AppError):
    """Cancellation request for long running operations."""

    default_code = ErrorCode.CANCELLED


def error_code_for_exception(exc: BaseException) -> ErrorCode:
    """Map any exception to a stable ErrorCode for boundary handling."""
    if isinstance(exc, AppError):
        return exc.code
    return ErrorCode.INTERNAL


def format_boundary_error_message(exc: BaseException) -> str:
    """Format a boundary-safe message prefixed with a stable error code."""
    code = error_code_for_exception(exc).value
    return f"[{code}] {exc}"
