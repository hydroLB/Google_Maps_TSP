"""Validation helpers for core TSP algorithms.

Keeps algorithm inputs safe and predictable."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def validate_square_matrix(matrix: Sequence[Sequence[float]], *, location: str) -> None:
    """Validate that a matrix is square and numeric.

    Prevents undefined behavior from invalid inputs."""
    try:
        if not isinstance(location, str) or not location.strip():
            raise ValidationError(
                "fastest_route.core.algorithms.validation.validate_square_matrix",
                "location must be a non empty string.",
            )
        if not matrix:
            raise ValidationError(location, "Matrix must not be empty.")
        size = len(matrix)
        for row_index, row in enumerate(matrix):
            try:
                row_size = len(row)
            except TypeError as exc:
                raise ValidationError(
                    location,
                    f"Matrix row {row_index} must be a sequence.",
                ) from exc
            if row_size != size:
                raise ValidationError(location, "Matrix must be square.")
            for col_index, value in enumerate(row):
                coordinates = f"({row_index}, {col_index})"
                if isinstance(value, bool):
                    raise ValidationError(
                        location,
                        f"Matrix value at {coordinates} must not be a boolean.",
                    )
                if not isinstance(value, int | float):
                    raise ValidationError(
                        location,
                        f"Matrix value at {coordinates} must be a real number.",
                    )
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValidationError(
                        location,
                        f"Matrix value at {coordinates} must be finite.",
                    )
                if value < 0:
                    raise ValidationError(
                        location,
                        f"Matrix value at {coordinates} must be zero or greater.",
                    )
    except ValidationError:
        raise
    except TypeError as exc:
        raise ValidationError(location, "Matrix must be a sequence of sequences.") from exc
