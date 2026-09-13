from __future__ import annotations

from fastest_route.presentation.gui.app.controllers.address_status_controller import (
    _present_status,
)
from fastest_route.presentation.gui.app.controllers.address_status_logic import (
    compute_address_status,
)
from fastest_route.shared.errors import ExternalServiceError, ValidationError


def test_present_status_maps_known_codes() -> None:
    """Keeps visual feedback stable for common status outcomes."""
    assert _present_status("OK") == ("Valid", "Status.Ok.TLabel")
    assert _present_status("KEY") == ("API key needed", "Status.Warn.TLabel")
    assert _present_status("ERR") == ("Check input", "Status.Error.TLabel")
    assert _present_status("SERVICE") == ("Service unavailable", "Status.Warn.TLabel")


def test_present_status_falls_back_for_unknown_values() -> None:
    """Prevents unexpected status strings from leaking noisy labels into the UI."""
    assert _present_status("SOMETHING_NEW") == ("", "Status.Info.TLabel")


class _StatusClient:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def has_api_key(self) -> bool:
        return True

    def geocode(self, _address: str, *, select_callback: object = None) -> str:
        if self._error is not None:
            raise self._error
        return "Resolved"


def test_address_status_distinguishes_input_and_provider_failures() -> None:
    """A provider outage must not tell users that a valid address is wrong."""
    invalid = _StatusClient(ValidationError("test", "no match"))
    unavailable = _StatusClient(ExternalServiceError("test", "timeout"))

    assert compute_address_status(maps_client=invalid, address_raw="Times Square") == "ERR"  # type: ignore[arg-type]
    assert compute_address_status(maps_client=unavailable, address_raw="Times Square") == "SERVICE"  # type: ignore[arg-type]
