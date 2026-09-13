from __future__ import annotations

import io
import json
import logging

import pytest

from fastest_route.observability import context as context_module, logger as logger_module
from fastest_route.observability.context import (
    correlation_context,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from fastest_route.observability.logger import (
    LOG_SCHEMA_VERSION,
    LOG_SERVICE_NAME,
    StructuredAdapter,
    StructuredFormatter,
    get_logger,
    setup_logging,
)
from fastest_route.shared.errors import ValidationError


def test_correlation_context_sets_id() -> None:
    """Ensures correlation ids are scoped correctly."""
    with correlation_context("abc"):
        assert get_correlation_id() == "abc"


def test_structured_formatter_includes_correlation_id() -> None:
    """Ensures logs are traceable with correlation ids."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("test_logger")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel("INFO")

    set_correlation_id("xyz")
    logger.info("hello")
    payload = json.loads(stream.getvalue())
    assert payload["correlation_id"] == "xyz"
    assert payload["message"] == "hello"
    assert payload["schema_version"] == LOG_SCHEMA_VERSION
    assert payload["service"] == LOG_SERVICE_NAME
    assert payload["event"] == "log.message"
    assert isinstance(payload["fields"], dict)


def test_setup_logging_and_adapter() -> None:
    """Ensures structured logging can be initialized."""
    setup_logging("INFO")
    logger = get_logger("adapter_test", component="test_component")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    base_logger = logging.getLogger("adapter_test")
    base_logger.handlers = [handler]
    base_logger.propagate = False
    base_logger.setLevel("INFO")

    assert isinstance(logger, StructuredAdapter)
    logger.info("adapter message")
    payload = json.loads(stream.getvalue())
    assert payload["component"] == "test_component"


def test_redaction_masks_sensitive_fields() -> None:
    """Ensures secrets do not leak in logs."""
    payload = {"api_key": "secret-value", "safe": "ok"}
    redacted = logger_module._redact_fields(payload)
    assert redacted["safe"] == "ok"
    assert redacted["api_key"] != "secret-value"


def test_redact_value_short_string() -> None:
    """Ensures short secrets are masked safely."""
    redacted = logger_module._redact_value("short")
    assert redacted == "***"


def test_redact_fields_hashes_pii_and_preserves_existing_tokens() -> None:
    """Ensures logs remain useful for correlation without leaking raw address-like values."""
    payload = {"origin": "123 Main St", "destination": "a1b2c3d4", "query": "hash:deadbeef"}
    redacted = logger_module._redact_fields(payload)
    assert isinstance(redacted["origin"], str)
    assert str(redacted["origin"]).startswith("hash:")
    assert "123" not in str(redacted["origin"])
    assert redacted["destination"] == "hash:a1b2c3d4"
    assert redacted["query"] == "hash:deadbeef"


def test_structured_formatter_emits_fields_and_redacts_extras() -> None:
    """The main value of structured logging is attaching useful context to errors without risking secret leakage."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("fields_logger")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel("INFO")

    logger.info(
        "hello",
        extra={
            "origin": "123 Main St",
            "api_key": "abcd1234",
            "count": 1,
            "url": "http://example.test/path?key=secret&token=also-secret",
            "headers": {"Authorization": "Bearer abcdefghijkl"},
        },
    )
    payload = json.loads(stream.getvalue())
    assert payload["message"] == "hello"
    assert "fields" in payload
    fields = payload["fields"]
    assert fields["count"] == 1
    assert fields["api_key"] == "***"
    assert isinstance(fields["origin"], str)
    assert fields["origin"].startswith("hash:")
    assert "123" not in fields["origin"]
    assert "key=<redacted>" in fields["url"]
    assert "token=<redacted>" in fields["url"]
    assert fields["headers"]["Authorization"] == "***"


def test_structured_formatter_promotes_error_code_to_top_level() -> None:
    """Error dashboards and alerts require a stable top-level error code field."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("error_code_logger")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel("INFO")

    logger.error("failed", extra={"error_code": "E_EXTERNAL_IO", "event": "routing.failed"})
    payload = json.loads(stream.getvalue())
    assert payload["error_code"] == "E_EXTERNAL_IO"
    assert payload["event"] == "routing.failed"


def test_structured_formatter_scrubs_inline_secrets_from_message() -> None:
    """Secret tokens can appear in message strings and must be redacted by default."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("message_redaction_logger")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel("INFO")

    logger.info("request failed key=abc123 token=xyz456")
    payload = json.loads(stream.getvalue())
    assert "abc123" not in payload["message"]
    assert "xyz456" not in payload["message"]
    assert "key=<redacted>" in payload["message"]
    assert "token=<redacted>" in payload["message"]


def test_correlation_id_propagates_across_logger_adapters() -> None:
    """Cross-module request tracing depends on consistent correlation id propagation."""
    stream_a = io.StringIO()
    stream_b = io.StringIO()
    handler_a = logging.StreamHandler(stream_a)
    handler_a.setFormatter(StructuredFormatter())
    handler_b = logging.StreamHandler(stream_b)
    handler_b.setFormatter(StructuredFormatter())

    base_a = logging.getLogger("module_a")
    base_a.handlers = [handler_a]
    base_a.propagate = False
    base_a.setLevel("INFO")
    base_b = logging.getLogger("module_b")
    base_b.handlers = [handler_b]
    base_b.propagate = False
    base_b.setLevel("INFO")

    logger_a = get_logger("module_a", component="module_a")
    logger_b = get_logger("module_b", component="module_b")
    with correlation_context("cid-123"):
        logger_a.info("a")
        logger_b.info("b")

    payload_a = json.loads(stream_a.getvalue())
    payload_b = json.loads(stream_b.getvalue())
    assert payload_a["correlation_id"] == "cid-123"
    assert payload_b["correlation_id"] == "cid-123"


def test_scrub_inline_secrets_handles_bearer_and_authorization() -> None:
    """URLs and headers are common accidental log fields; scrubbing must be safe by default."""
    assert logger_module._scrub_inline_secrets("Bearer abcdef") == "Bearer <redacted>"
    assert logger_module._scrub_inline_secrets("Authorization: Bearer abcdef") == "<redacted>"


def test_to_jsonable_serializes_common_types() -> None:
    """Log extras may contain bytes, exceptions, sets, or enums and must not break formatting."""

    class ValueEnumLike:
        value = "enum-value"

    assert logger_module._to_jsonable(b"\x00\x01") == "<bytes>"
    assert logger_module._to_jsonable({"a": 1, "b": {"c": 2}}) == {"a": 1, "b": {"c": 2}}
    assert logger_module._to_jsonable({1, 2}) in ([1, 2], [2, 1])
    assert logger_module._to_jsonable(ValueError("boom")) == "boom"
    assert logger_module._to_jsonable(ValueEnumLike()) == "enum-value"


def test_redact_value_handles_non_string_values() -> None:
    """Secrets can be passed as non-string values at call sites; redaction must still be safe."""
    assert logger_module._redact_value(123) == "***"


def test_hash_value_rejects_non_string() -> None:
    """Prevents accidental hashing of non-string values which could hide upstream bugs."""
    with pytest.raises(ValidationError):
        logger_module._hash_value(123)  # type: ignore[arg-type]


def test_structured_formatter_includes_exception() -> None:
    """Ensures exceptions appear in structured output."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("exception_logger")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel("INFO")
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("failed")
    payload = json.loads(stream.getvalue())
    assert "exception" in payload


def test_structured_adapter_non_mapping_extra() -> None:
    """Ensures adapters handle non mapping extras safely."""
    adapter = StructuredAdapter(logging.getLogger("extra_logger"), {"component": "extra"})
    msg, kwargs = adapter.process("message", {"extra": "not-mapping"})
    assert msg == "message"
    assert isinstance(kwargs["extra"], dict)


def test_generate_correlation_id_handles_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures id generation failures surface as ValidationError."""
    monkeypatch.setattr(
        context_module, "uuid4", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(ValidationError):
        generate_correlation_id()


def test_get_correlation_id_handles_lookup_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures lookup failures surface as ValidationError."""

    class FailingGetContextVar:
        def get(self) -> str:
            raise LookupError("boom")

    monkeypatch.setattr(context_module, "CORRELATION_ID", FailingGetContextVar())
    with pytest.raises(ValidationError):
        get_correlation_id()


def test_set_correlation_id_rejects_non_string() -> None:
    """Ensures correlation ids must be strings."""
    with pytest.raises(ValidationError):
        set_correlation_id(123)


def test_set_correlation_id_handles_set_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures set failures surface as ValidationError."""

    class FailingSetContextVar:
        def set(self, _value: str) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(context_module, "CORRELATION_ID", FailingSetContextVar())
    with pytest.raises(ValidationError):
        set_correlation_id("test")


def test_correlation_context_rejects_non_string() -> None:
    """Ensures correlation ids must be strings when provided."""
    with pytest.raises(ValidationError), correlation_context(123):
        pass


def test_correlation_context_handles_reset_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures reset failures surface as ValidationError."""

    class FailingResetContextVar:
        def set(self, _value: str) -> str:
            return "token"

        def reset(self, _token: str) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(context_module, "CORRELATION_ID", FailingResetContextVar())
    with pytest.raises(ValidationError), correlation_context("test"):
        pass


def test_redact_fields_rejects_non_mapping() -> None:
    """Ensures redaction requires mapping payloads."""
    with pytest.raises(ValidationError):
        logger_module._redact_fields(["bad"])


def test_utc_timestamp_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures timestamp formatting errors surface."""
    monkeypatch.setattr(
        logger_module,
        "datetime",
        type(
            "BadDatetime", (), {"now": lambda *_a, **_k: (_ for _ in ()).throw(ValueError("boom"))}
        ),
    )
    with pytest.raises(ValidationError):
        logger_module._utc_timestamp()


def test_structured_formatter_wraps_format_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures formatting failures raise ValidationError."""
    formatter = StructuredFormatter()
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "msg", (), None)
    monkeypatch.setattr(
        logger_module.json, "dumps", lambda *_a, **_k: (_ for _ in ()).throw(TypeError("boom"))
    )
    with pytest.raises(ValidationError):
        formatter.format(record)


def test_structured_adapter_process_handles_errors() -> None:
    """Ensures invalid kwargs surface as ValidationError."""
    adapter = StructuredAdapter(logging.getLogger("bad_logger"), {"component": "bad"})
    with pytest.raises(ValidationError):
        adapter.process("message", None)


def test_setup_logging_rejects_empty_level() -> None:
    """Ensures logging level is required."""
    with pytest.raises(ValidationError):
        setup_logging(" ")


def test_get_logger_rejects_empty_name() -> None:
    """Ensures logger names are required."""
    with pytest.raises(ValidationError):
        get_logger(" ")
