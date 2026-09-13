"""Parsing and validation helpers for guided-entry text input."""

from __future__ import annotations

from fastest_route.shared.errors import ValidationError


def parse_guided_entry_lines(*, raw_text: str, min_stops: int, max_stops: int) -> list[str]:
    """Parse guided-entry text into a validated list of lines."""
    location = (
        "fastest_route.presentation.gui.app.workflow.guided_entry_parser.parse_guided_entry_lines"
    )
    if not isinstance(raw_text, str):
        raise ValidationError(location, "raw_text must be a string.")
    if min_stops <= 0:
        raise ValidationError(location, "min_stops must be positive.")
    if max_stops <= 0:
        raise ValidationError(location, "max_stops must be positive.")
    if max_stops < min_stops:
        raise ValidationError(location, "max_stops must be greater than or equal to min_stops.")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if len(lines) < min_stops:
        raise ValidationError(location, f"At least {min_stops} stops are required.")
    if len(lines) > max_stops:
        raise ValidationError(location, f"At most {max_stops} stops are supported.")
    return lines
