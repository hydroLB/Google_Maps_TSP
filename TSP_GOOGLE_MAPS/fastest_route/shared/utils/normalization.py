"""Normalize user input strings into addresses suitable for geocoding."""

from __future__ import annotations

import re
from urllib.parse import unquote, unquote_plus

from fastest_route.shared.errors import ValidationError


def _looks_like_coordinates(value: str) -> bool:
    """Check if a string looks like a latitude,longitude coordinate pair."""
    try:
        return bool(
            re.fullmatch(
                r"-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?",
                value.strip(),
            )
        )
    except re.error:
        return False


def normalize_address_input(value: str) -> str:
    """Normalize a single address input."""
    location = "fastest_route.shared.utils.normalization.normalize_address_input"
    if not isinstance(value, str):
        raise ValidationError(location, "Address input must be a string.")
    try:
        text = value.strip()
        if _looks_like_coordinates(text):
            raise ValidationError(
                location,
                "Coordinates are not supported. Provide a street address or a Google Maps place link.",
            )
        url_pattern = re.compile(
            r"(https?://)?(www\.)?(google\.com/maps|maps\.app\.goo\.gl|goo\.gl/maps)\S*",
            re.IGNORECASE,
        )
        if url_pattern.match(text):
            place_match = re.search(r"/maps/place/([^/]+)", text)
            if place_match:
                place = unquote_plus(place_match.group(1))
                if _looks_like_coordinates(place):
                    raise ValidationError(
                        location,
                        "Google Maps links pointing only to coordinates are not supported. Provide a place link or a street address.",
                    )
                return place
            dir_match = re.search(r"(?:origin|destination)=([^&]+)", text)
            if dir_match:
                extracted = unquote(dir_match.group(1))
                if _looks_like_coordinates(extracted):
                    raise ValidationError(
                        location,
                        "Direction links that contain only coordinates are not supported. Provide a street address or a Google Maps place link.",
                    )
                return extracted
            if re.search(r"/maps/@-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?", text):
                raise ValidationError(
                    location,
                    "Google Maps links that contain only coordinates are not supported. Provide a place link or a street address.",
                )
            raise ValidationError(
                location,
                "Google Maps link could not be parsed. Provide a street address or a Google Maps place link.",
            )
        return re.sub(r"\s+", " ", text)
    except re.error as exc:
        raise ValidationError(location, "Failed to normalize address input.") from exc
