"""Structured logging with correlation ids and safe handling of sensitive fields."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastest_route.observability.context import get_correlation_id
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import MutableMapping

LOG_SCHEMA_VERSION = "1.0"
LOG_SERVICE_NAME = "fastest_route_optimizer"
_PROCESS_LOG_HASH_KEY = secrets.token_bytes(32)


_LOG_RECORD_RESERVED_FIELDS: set[str] = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
    "event",
    "error_code",
}


def _utc_timestamp() -> str:
    """Generate an ISO 8601 UTC timestamp for logs."""
    location = "fastest_route.observability.logger._utc_timestamp"
    try:
        return datetime.now(UTC).isoformat(timespec="milliseconds")
    except ValueError as exc:
        raise ValidationError(location, "Failed to format timestamp.") from exc


def _redact_value(value: object) -> object:
    """Redact sensitive values before logging."""
    location = "fastest_route.observability.logger._redact_value"
    try:
        if isinstance(value, str):
            return "***"
        return "***"
    except Exception as exc:
        raise ValidationError(location, "Failed to redact value.") from exc


def _is_short_hex_digest(value: str) -> bool:
    """Recognize existing short digests so redaction does not hash them twice."""
    if not isinstance(value, str) or len(value) != 8:
        return False
    return all(ch in "0123456789abcdef" for ch in value.lower())


def _hash_value(value: str) -> str:
    """Create a process-scoped correlation token for a sensitive string."""
    location = "fastest_route.observability.logger._hash_value"
    if not isinstance(value, str):
        raise ValidationError(location, "value must be a string.")
    try:
        payload = _PROCESS_LOG_HASH_KEY + b"\0" + value.encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:8]
    except (AttributeError, UnicodeEncodeError) as exc:
        raise ValidationError(location, "Failed to hash value.") from exc


def _scrub_inline_secrets(text: str) -> str:
    """Scrub common secret patterns from otherwise unstructured log text."""
    if not isinstance(text, str) or not text:
        return str(text)
    lowered = text.lower()
    if (
        "key=" not in lowered
        and "token=" not in lowered
        and "authorization" not in lowered
        and "bearer " not in lowered
    ):
        return text
    # Minimal, best-effort scrubbing without regex dependencies in hot paths.
    replacements = [
        ("key=", "key=<redacted>"),
        ("api_key=", "api_key=<redacted>"),
        ("token=", "token=<redacted>"),
    ]
    scrubbed = text
    for needle, replacement in replacements:
        idx = scrubbed.lower().find(needle)
        if idx == -1:
            continue
        # Replace the value segment up to the next delimiter.
        start = idx
        end = start + len(needle)
        while end < len(scrubbed) and scrubbed[end] not in {"&", " ", "\n", "\t", "\r"}:
            end += 1
        scrubbed = scrubbed[:start] + replacement + scrubbed[end:]
    if "bearer " in scrubbed.lower():
        parts = scrubbed.split()
        if len(parts) >= 2 and parts[0].lower() == "bearer":
            scrubbed = "Bearer <redacted>"
    if "authorization" in scrubbed.lower():
        return "<redacted>"
    return scrubbed


def _to_jsonable(value: object) -> object:
    """Convert arbitrary objects into JSON-serializable structures."""
    try:
        if value is None:
            return None
        if isinstance(value, bool | int | float):
            return value
        if isinstance(value, str):
            return _scrub_inline_secrets(value)
        if isinstance(value, bytes):
            return "<bytes>"
        if isinstance(value, Mapping):
            out: dict[str, object] = {}
            for k, v in value.items():
                out[str(k)] = _to_jsonable(v)
            return out
        if isinstance(value, list | tuple | set):
            return [_to_jsonable(item) for item in value]
        if isinstance(value, BaseException):
            return str(value)
        enum_value = getattr(value, "value", None)
        if enum_value is not None and isinstance(enum_value, str | int | float | bool):
            return enum_value
        return str(value)
    except Exception:
        return "<unserializable>"


def _redact_fields(payload: Mapping[str, object]) -> dict[str, object]:
    """Remove secrets and hash PII-like fields before log serialization."""
    location = "fastest_route.observability.logger._redact_fields"
    if not isinstance(payload, Mapping):
        raise ValidationError(location, "payload must be a mapping.")
    try:
        redacted: dict[str, object] = {}
        secret_keys = {
            "api_key",
            "key",
            "token",
            "secret",
            "authorization",
            "password",
            "cookie",
            "set-cookie",
            "session",
            "access_token",
            "refresh_token",
        }
        pii_keys = {"address", "origin", "destination", "from", "to", "waypoints", "query"}

        def redact_any(obj: object, *, field_name: str | None = None) -> object:
            if isinstance(obj, Mapping):
                return {str(k): redact_any(v, field_name=str(k)) for k, v in obj.items()}
            if isinstance(obj, list | tuple | set):
                return [redact_any(item, field_name=field_name) for item in obj]
            if field_name is not None:
                lowered = field_name.lower()
                if lowered in secret_keys:
                    return _redact_value(obj)
                if lowered in pii_keys and isinstance(obj, str) and obj.strip():
                    value = obj.strip()
                    if value.lower().startswith("hash:"):
                        return value
                    if _is_short_hex_digest(value):
                        return f"hash:{value}"
                    return f"hash:{_hash_value(value)}"
            return _to_jsonable(obj)

        for field, value in payload.items():
            redacted[str(field)] = redact_any(value, field_name=str(field))
        return redacted
    except Exception as exc:
        raise ValidationError(location, "Failed to redact fields.") from exc


def _extract_record_fields(record: logging.LogRecord) -> dict[str, object]:
    """Extract user-provided structured fields from a LogRecord."""
    try:
        fields: dict[str, object] = {}
        for key, value in record.__dict__.items():
            if key in _LOG_RECORD_RESERVED_FIELDS:
                continue
            if key in {"correlation_id", "component"}:
                continue
            if key.startswith("_"):
                continue
            fields[str(key)] = value
        return fields
    except Exception:
        return {}


class StructuredFormatter(logging.Formatter):
    """Emit structured JSON logs with consistent fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record into structured JSON."""
        location = "fastest_route.observability.logger.StructuredFormatter.format"
        try:
            payload: dict[str, object] = {
                "schema_version": LOG_SCHEMA_VERSION,
                "service": LOG_SERVICE_NAME,
                "timestamp": _utc_timestamp(),
                "level": record.levelname,
                "logger": record.name,
                "event": getattr(record, "event", "log.message"),
                "message": record.getMessage(),
                "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
                "component": getattr(record, "component", record.name),
            }
            fields = _extract_record_fields(record)
            error_code = getattr(record, "error_code", None)
            if error_code:
                payload["error_code"] = str(error_code)
            payload["fields"] = fields
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(_redact_fields(payload), ensure_ascii=True)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(location, "Failed to format log record.") from exc


class StructuredAdapter(logging.LoggerAdapter[logging.Logger]):
    """Attach structured context fields to log records."""

    def process(
        self, msg: object, kwargs: MutableMapping[str, object]
    ) -> tuple[object, MutableMapping[str, object]]:
        """Inject correlation and component fields into log extras."""
        location = "fastest_route.observability.logger.StructuredAdapter.process"
        try:
            extra_fields: dict[str, object] = {}
            for key, value in dict(self.extra or {}).items():
                extra_fields[str(key)] = value
            extra_fields.setdefault("correlation_id", get_correlation_id())

            normalized_kwargs: dict[str, object] = {}
            for key, value in dict(kwargs).items():
                normalized_kwargs[str(key)] = value

            existing_extra = normalized_kwargs.get("extra")
            merged_extra = dict(extra_fields)
            if isinstance(existing_extra, Mapping):
                for key, value in existing_extra.items():
                    merged_extra[str(key)] = value
            normalized_kwargs["extra"] = merged_extra
            return msg, normalized_kwargs
        except Exception as exc:
            raise ValidationError(location, "Failed to assemble log context.") from exc


def setup_logging(level: str) -> None:
    """Configure root logging with a structured formatter."""
    location = "fastest_route.observability.logger.setup_logging"
    if not isinstance(level, str) or not level.strip():
        raise ValidationError(location, "level must be a non empty string.")
    try:
        logging.basicConfig(level=level.upper())
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(level.upper())
    except Exception as exc:
        raise ValidationError(location, "Failed to configure logging.") from exc


def get_logger(name: str, *, component: str | None = None) -> StructuredAdapter:
    """Create a structured logger adapter."""
    location = "fastest_route.observability.logger.get_logger"
    if not isinstance(name, str) or not name.strip():
        raise ValidationError(location, "name must be a non empty string.")
    try:
        base_logger = logging.getLogger(name)
        return StructuredAdapter(base_logger, {"component": component or name})
    except Exception as exc:
        raise ValidationError(location, "Failed to create logger adapter.") from exc
