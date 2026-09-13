"""GoogleMapsClient request helpers for credentials, geocoding, autocomplete, and HTTP execution."""

from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from fastest_route.infrastructure.google_maps import client as client_module
from fastest_route.infrastructure.google_maps.client_support.base import GoogleMapsClientHost
from fastest_route.infrastructure.google_maps.parsing import (
    parse_autocomplete_suggestions,
    parse_geocode_formatted_addresses,
    select_single_or_prompt,
)
from fastest_route.infrastructure.google_maps.redaction import redact_address
from fastest_route.observability.logger import get_logger
from fastest_route.shared.errors import (
    CacheError,
    ExternalServiceError,
    ValidationError,
    format_boundary_error_message,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fastest_route.shared.cancellation import CancellationToken

logger = get_logger(__name__, component="google_maps")


class GoogleMapsClientRequestMixin(GoogleMapsClientHost):
    """Provide GoogleMapsClient methods for request execution and lightweight API lookups."""

    def _api_key(self, location: str) -> str:
        """Resolve the API key for outbound requests."""
        key = self._api_key_override or self._config.google_maps.api_key
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(
                location,
                "Google Maps API key is not configured. Use the GUI 'Set API Key' action or set GOOGLE_MAPS_API_KEY.",
            )
        return key.strip()

    def close(self) -> None:
        location = "fastest_route.infrastructure.google_maps.client_support.requests.GoogleMapsClientRequestMixin.close"
        try:
            self._session.close()
        except requests.RequestException as exc:
            raise ExternalServiceError(location, "Failed to close HTTP session.") from exc

    def _redact_address(self, address: str) -> str:
        """Create a short address token for logs without exposing the address."""
        location = "fastest_route.infrastructure.google_maps.client_support.requests.GoogleMapsClientRequestMixin._redact_address"
        return redact_address(address, location=location, sha256=client_module.hashlib.sha256)

    def _request_json(
        self,
        url: str,
        params: Mapping[str, str],
        *,
        cancellation_token: CancellationToken | None = None,
        deadline: float | None = None,
    ) -> Mapping[str, object]:
        """Execute a cancellable HTTP GET and return its JSON mapping."""
        location = "fastest_route.infrastructure.google_maps.client_support.requests.GoogleMapsClientRequestMixin._request_json"
        if not isinstance(url, str) or not url.strip():
            raise ValidationError(location, "url must be a non empty string.")
        try:
            return self._http.get_json(
                url,
                params,
                location=location,
                cancellation_token=cancellation_token,
                deadline=deadline,
            )
        except ExternalServiceError as exc:
            raise type(exc)(location, format_boundary_error_message(exc)) from exc
        except ValidationError as exc:
            raise ExternalServiceError(
                location,
                f"{format_boundary_error_message(exc)} Request validation failed.",
            ) from exc

    def geocode(
        self,
        address: str,
        *,
        select_callback: Callable[[Sequence[str]], str | None] | None = None,
    ) -> str:
        """Resolve an address to a canonical formatted address."""
        location = "fastest_route.infrastructure.google_maps.client_support.requests.GoogleMapsClientRequestMixin.geocode"
        if not isinstance(address, str):
            raise ValidationError(location, "Address must be a string.")
        if select_callback is not None and not callable(select_callback):
            raise ValidationError(location, "select_callback must be callable when provided.")
        if not address.strip():
            raise ValidationError(location, "Address must be provided.")
        try:
            cached = self._read_geocode_cache(address=address)
            if cached is not None:
                return cached
            formatted = self._retry_policy.execute(
                lambda: parse_geocode_formatted_addresses(
                    self._request_json(
                        self._config.google_maps.geocode_url,
                        {"address": address, "key": self._api_key(location)},
                    ),
                    location=location,
                ),
                location=location,
            )
            resolved = select_single_or_prompt(
                formatted,
                select_callback=select_callback,
                location=location,
            )
            self._write_geocode_cache(address=address, resolved=resolved)
            return resolved
        except ExternalServiceError:
            raise
        except ValidationError:
            raise
        except (KeyError, TypeError) as exc:
            raise ExternalServiceError(location, "Geocoding response was invalid.") from exc

    def autocomplete(self, query: str) -> list[str]:
        """Fetch autocomplete suggestions for a query."""
        location = "fastest_route.infrastructure.google_maps.client_support.requests.GoogleMapsClientRequestMixin.autocomplete"
        if not isinstance(query, str):
            raise ValidationError(location, "Autocomplete query must be a string.")
        if not query.strip():
            raise ValidationError(location, "Autocomplete query must not be empty.")
        try:
            return self._retry_policy.execute(
                lambda: parse_autocomplete_suggestions(
                    self._request_json(
                        self._config.google_maps.places_autocomplete_url,
                        {"input": query, "key": self._api_key(location), "types": "geocode"},
                    ),
                    location=location,
                ),
                location=location,
            )
        except ExternalServiceError:
            raise
        except (KeyError, TypeError) as exc:
            raise ExternalServiceError(location, "Autocomplete response was invalid.") from exc

    def _read_geocode_cache(self, *, address: str) -> str | None:
        """Treat cache-read failures as non-fatal while preserving observability."""
        try:
            return self._geocode_cache.get(address)
        except CacheError as exc:
            logger.warning(
                "Geocode cache read failed",
                extra={"error": str(exc), "address": self._redact_address(address)},
            )
            return None

    def _write_geocode_cache(self, *, address: str, resolved: str) -> None:
        """Treat cache-write failures as non-fatal while preserving observability."""
        try:
            self._geocode_cache.set(address, resolved)
        except CacheError as exc:
            logger.warning(
                "Geocode cache write failed",
                extra={"error": str(exc), "address": self._redact_address(address)},
            )
