"""Cancellation token for cooperative shutdown of long operations."""

from __future__ import annotations

import threading

from fastest_route.shared.errors import CancellationError


class CancellationToken:
    """Cooperative cancellation state shared across components."""

    def __init__(self) -> None:
        location = "fastest_route.shared.cancellation.CancellationToken.__init__"
        try:
            self._event = threading.Event()
        except RuntimeError as exc:
            raise CancellationError(location, "Failed to initialize cancellation token.") from exc

    def cancel(self) -> None:
        """Signal cancellation to observers."""
        location = "fastest_route.shared.cancellation.CancellationToken.cancel"
        try:
            self._event.set()
        except RuntimeError as exc:
            raise CancellationError(location, "Failed to signal cancellation.") from exc

    def is_cancelled(self) -> bool:
        """Check whether cancellation has been requested."""
        location = "fastest_route.shared.cancellation.CancellationToken.is_cancelled"
        try:
            return self._event.is_set()
        except RuntimeError as exc:
            raise CancellationError(location, "Failed to read cancellation state.") from exc

    def raise_if_cancelled(self, location: str) -> None:
        """Raise a cancellation error if cancelled."""
        check_location = "fastest_route.shared.cancellation.CancellationToken.raise_if_cancelled"
        try:
            if self.is_cancelled():
                raise CancellationError(location, "Operation cancelled by caller.")
        except CancellationError:
            raise
        except RuntimeError as exc:
            raise CancellationError(
                check_location, "Failed to evaluate cancellation state."
            ) from exc
