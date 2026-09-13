"""Response parsing helpers for Google Maps JSON payloads.

Separates payload validation from IO so future endpoint changes are easier to localize."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from fastest_route.shared.errors import (
    ExternalServiceError,
    RetryableExternalServiceError,
    ValidationError,
)
from fastest_route.shared.types import OptimizeFor

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_RETRYABLE_API_STATUSES = frozenset({"OVER_QUERY_LIMIT", "UNKNOWN_ERROR"})


def _raise_for_api_status(*, service: str, status: object, location: str) -> None:
    """Raise a retryable error only for provider statuses documented as transient."""

    message = f"{service} status {status}."
    if status in _RETRYABLE_API_STATUSES:
        raise RetryableExternalServiceError(location, message)
    raise ExternalServiceError(location, message)


def parse_geocode_formatted_addresses(payload: Mapping[str, object], *, location: str) -> list[str]:
    """Extract formatted address strings from a Google geocode response payload.

    Keeps geocode parsing deterministic and easy to test in isolation."""
    if not isinstance(location, str) or not location.strip():
        raise ValidationError(
            "fastest_route.infrastructure.google_maps.parsing.parse_geocode_formatted_addresses",
            "location must be set.",
        )
    status = payload.get("status")
    if status != "OK":
        _raise_for_api_status(service="Geocoding", status=status, location=location)
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise ExternalServiceError(location, "Geocoding response contained no results.")
    formatted: list[str] = []
    for entry in results:
        if isinstance(entry, Mapping):
            value = entry.get("formatted_address")
            if isinstance(value, str):
                formatted.append(value)
    if not formatted:
        raise ExternalServiceError(location, "No formatted addresses returned.")
    return formatted


def select_single_or_prompt(
    options: Sequence[str],
    *,
    select_callback: Callable[[Sequence[str]], str | None] | None,
    location: str,
) -> str:
    """Select a single option, prompting through a callback when multiple exist.

    Keeps selection rules consistent across features that may need user choice."""
    if not options:
        raise ValidationError(location, "No options were provided for selection.")
    if len(options) == 1:
        return options[0]
    if select_callback is None:
        raise ValidationError(location, "Multiple results but no selection callback provided.")
    selection = select_callback(options)
    if selection is None or not isinstance(selection, str) or not selection.strip():
        raise ValidationError(location, "No address selection was made.")
    return selection


def parse_autocomplete_suggestions(payload: Mapping[str, object], *, location: str) -> list[str]:
    """Extract autocomplete suggestion descriptions from a payload.

    Centralizes the payload traversal so API changes are localized."""
    if not isinstance(location, str) or not location.strip():
        raise ValidationError(
            "fastest_route.infrastructure.google_maps.parsing.parse_autocomplete_suggestions",
            "location must be set.",
        )
    status = payload.get("status")
    if status == "ZERO_RESULTS":
        return []
    if status != "OK":
        _raise_for_api_status(service="Autocomplete", status=status, location=location)
    predictions = payload.get("predictions")
    if not isinstance(predictions, list):
        return []
    suggestions: list[str] = []
    for entry in predictions:
        if isinstance(entry, Mapping):
            description = entry.get("description")
            if isinstance(description, str):
                suggestions.append(description)
    return suggestions


def parse_distance_matrix_value(
    payload: Mapping[str, object],
    *,
    metric: OptimizeFor,
    use_duration_in_traffic: bool = False,
    location: str,
) -> float:
    """Parse a distance matrix response payload into a single numeric value.

    Keeps payload structure validation centralized and consistent."""
    if not isinstance(location, str) or not location.strip():
        raise ValidationError(
            "fastest_route.infrastructure.google_maps.parsing.parse_distance_matrix_value",
            "location must be set.",
        )
    status = payload.get("status")
    if status != "OK":
        _raise_for_api_status(service="Distance matrix", status=status, location=location)
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ExternalServiceError(location, "Distance matrix rows missing.")
    first_row = rows[0]
    if not isinstance(first_row, Mapping):
        raise ExternalServiceError(location, "Distance matrix row invalid.")
    elements = first_row.get("elements")
    if not isinstance(elements, list) or not elements:
        raise ExternalServiceError(location, "Distance matrix elements missing.")
    first_element = elements[0]
    if not isinstance(first_element, Mapping):
        raise ExternalServiceError(location, "Distance matrix element invalid.")
    return _parse_distance_element_value(
        first_element,
        metric=metric,
        use_duration_in_traffic=use_duration_in_traffic,
        location=location,
    )


def parse_distance_matrix_values(
    payload: Mapping[str, object],
    *,
    metric: OptimizeFor,
    expected_size: int,
    use_duration_in_traffic: bool = False,
    location: str,
) -> list[list[float]]:
    """Parse and validate a complete square matrix returned by Distance Matrix API.

    The application requests the same address set as origins and destinations. Requiring
    the exact expected shape prevents a partial provider response from silently producing
    a route with missing or misaligned legs.
    """

    if expected_size <= 0:
        raise ValidationError(location, "expected_size must be positive.")
    status = payload.get("status")
    if status != "OK":
        _raise_for_api_status(service="Distance matrix", status=status, location=location)
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != expected_size:
        raise ExternalServiceError(location, "Distance matrix row count did not match request.")

    matrix: list[list[float]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ExternalServiceError(location, f"Distance matrix row {row_index} was invalid.")
        elements = row.get("elements")
        if not isinstance(elements, list) or len(elements) != expected_size:
            raise ExternalServiceError(
                location,
                f"Distance matrix row {row_index} element count did not match request.",
            )
        parsed_row: list[float] = []
        for column_index, element in enumerate(elements):
            if not isinstance(element, Mapping):
                raise ExternalServiceError(
                    location,
                    f"Distance matrix element ({row_index}, {column_index}) was invalid.",
                )
            value = _parse_distance_element_value(
                element,
                metric=metric,
                use_duration_in_traffic=use_duration_in_traffic,
                location=location,
            )
            parsed_row.append(0.0 if row_index == column_index else value)
        matrix.append(parsed_row)
    return matrix


def _parse_distance_element_value(
    element: Mapping[str, object],
    *,
    metric: OptimizeFor,
    use_duration_in_traffic: bool,
    location: str,
) -> float:
    """Parse one matrix element into minutes or kilometers."""

    element_status = element.get("status")
    if element_status != "OK":
        raise ExternalServiceError(location, f"Distance matrix element status {element_status}.")

    if metric == OptimizeFor.TIME:
        field = "duration_in_traffic" if use_duration_in_traffic else "duration"
        duration = element.get(field)
        if not isinstance(duration, Mapping):
            label = "Traffic-aware duration" if use_duration_in_traffic else "Duration"
            raise ExternalServiceError(location, f"{label} payload missing.")
        value = duration.get("value")
        if not isinstance(value, int | float):
            label = "Traffic-aware duration" if use_duration_in_traffic else "Duration"
            raise ExternalServiceError(location, f"{label} value missing.")
        return float(value) / 60.0

    if metric != OptimizeFor.DISTANCE:
        raise ValidationError(location, "metric must be a supported OptimizeFor value.")
    distance = element.get("distance")
    if not isinstance(distance, Mapping):
        raise ExternalServiceError(location, "Distance payload missing.")
    value = distance.get("value")
    if not isinstance(value, int | float):
        raise ExternalServiceError(location, "Distance value missing.")
    return float(value) / 1000.0
