"""Presentation helpers for rendering route outputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def generate_route_lines(
    order: Sequence[int],
    addrs: Sequence[str],
    origs: Sequence[str],
    has_start: bool,
    has_end: bool,
    route_kind: str,
) -> str:
    """Render a multi line route listing for display."""
    location = "fastest_route.shared.utils.presenters.generate_route_lines"
    if len(addrs) != len(origs):
        raise ValidationError(location, "Addresses and originals length mismatch.")
    try:
        if route_kind == "round_trip":
            if has_end:
                raise ValidationError(location, "Round trips do not support a fixed end address.")
            if has_start:
                if not order or order[0] != 0:
                    raise ValidationError(location, "Route order must start with the fixed start.")
                header = f"Start/End: {addrs[0]}\n    (your input: {origs[0]})\n"
                body = "\n".join(
                    f"{i + 1}. {addrs[idx]}\n    (your input: {origs[idx]})"
                    for i, idx in enumerate(order[1:])
                )
                trailer = "\n\nReturn to start."
                return header + body + trailer if body else header + trailer
            body = "\n".join(
                f"{i + 1}. {addrs[idx]}\n    (your input: {origs[idx]})"
                for i, idx in enumerate(order)
            )
            trailer = f"\n\nReturn to {addrs[order[0]]}."
            return body + trailer

        if has_start and (not order or order[0] != 0):
            raise ValidationError(location, "Route order must start with the fixed start.")
        if has_end and (not order or order[-1] != len(addrs) - 1):
            raise ValidationError(location, "Route order must end with the fixed end.")

        lines: list[str] = []
        if has_start:
            lines.append(f"Start: {addrs[0]}\n    (your input: {origs[0]})")

        middle_indices = (
            order[1:-1]
            if has_start and has_end
            else (order[1:] if has_start else (order[:-1] if has_end else order))
        )
        for i, idx in enumerate(middle_indices, start=1):
            lines.append(f"{i}. {addrs[idx]}\n    (your input: {origs[idx]})")

        if has_end:
            end_idx = len(addrs) - 1
            lines.append(f"End: {addrs[end_idx]}\n    (your input: {origs[end_idx]})")

        return "\n".join(lines)
    except (IndexError, TypeError) as exc:
        raise ValidationError(location, "Failed to build route lines.") from exc
