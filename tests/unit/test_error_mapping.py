from __future__ import annotations

from fastest_route.shared.errors import (
    AppError,
    CancellationError,
    ConfigError,
    ErrorCode,
    ExternalServiceError,
    ValidationError,
    error_code_for_exception,
    format_boundary_error_message,
)


def test_error_code_for_exception_maps_known_app_errors() -> None:
    """Prevents taxonomy drift in boundary handlers."""
    assert error_code_for_exception(ConfigError("tests", "bad config")) == ErrorCode.CONFIG
    assert error_code_for_exception(ValidationError("tests", "bad input")) == ErrorCode.VALIDATION
    assert (
        error_code_for_exception(ExternalServiceError("tests", "io failed"))
        == ErrorCode.EXTERNAL_IO
    )
    assert error_code_for_exception(CancellationError("tests", "cancelled")) == ErrorCode.CANCELLED


def test_error_code_for_exception_maps_unknown_exceptions_to_internal() -> None:
    """Ensures boundary code mapping is total and never returns an undefined category."""
    assert error_code_for_exception(RuntimeError("boom")) == ErrorCode.INTERNAL


def test_format_boundary_error_message_prefixes_code() -> None:
    """Keeps boundary-visible error text machine-readable and consistent."""
    message = format_boundary_error_message(AppError("tests", "unexpected"))
    assert message.startswith("[E_INTERNAL] ")
    assert "tests: unexpected" in message
