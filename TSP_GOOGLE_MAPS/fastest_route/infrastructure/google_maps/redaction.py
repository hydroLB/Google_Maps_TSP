"""Redaction helpers for protecting sensitive user data in logs."""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING, Protocol

from fastest_route.shared.errors import ValidationError

_PROCESS_REDACTION_KEY = secrets.token_bytes(32)

if TYPE_CHECKING:
    from collections.abc import Callable


class _HexDigest(Protocol):
    """Describe the digest interface accepted by address redaction."""

    def hexdigest(self) -> str:
        raise NotImplementedError


def redact_address(
    address: str,
    *,
    location: str,
    sha256: Callable[[bytes], _HexDigest] | None = None,
) -> str:
    """Create a process-scoped address token for correlating logs without storing the address."""
    if not isinstance(location, str) or not location.strip():
        raise ValidationError(
            "fastest_route.infrastructure.google_maps.redaction.redact_address",
            "location must be set.",
        )
    if not isinstance(address, str):
        raise ValidationError(location, "Address must be a string for redaction.")
    if sha256 is None:
        sha256 = hashlib.sha256
    try:
        payload = _PROCESS_REDACTION_KEY + b"\0" + address.encode("utf-8")
        digest = sha256(payload).hexdigest()
        return digest[:8]
    except (AttributeError, UnicodeEncodeError) as exc:
        raise ValidationError(location, "Failed to redact address.") from exc
