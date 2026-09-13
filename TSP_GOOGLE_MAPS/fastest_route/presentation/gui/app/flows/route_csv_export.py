"""CSV export flow for the most recent optimized route."""

from __future__ import annotations

import csv
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from fastest_route.presentation.gui.app.flows.errors import strip_location_prefix
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import (
    RouteKind,
    RouteRequest,
    RouteResult,
    route_safety_warnings,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class RouteLegCsvRow:
    """Represent a single leg row for CSV export."""

    leg_index: int
    from_index: int
    to_index: int
    from_resolved: str
    to_resolved: str
    from_original: str
    to_original: str
    value: float
    cumulative: float
    units: str
    trip: str
    travel_mode: str
    optimize_for: str
    safety_warnings: str

    def as_dict(self) -> dict[str, object]:
        """Convert the row to a CSV writer compatible dictionary."""
        return {
            "leg_index": self.leg_index,
            "from_index": self.from_index,
            "to_index": self.to_index,
            "from_resolved": self.from_resolved,
            "to_resolved": self.to_resolved,
            "from_original": self.from_original,
            "to_original": self.to_original,
            "value": self.value,
            "cumulative": self.cumulative,
            "units": self.units,
            "trip": self.trip,
            "travel_mode": self.travel_mode,
            "optimize_for": self.optimize_for,
            "safety_warnings": self.safety_warnings,
        }


def _validate_leg_counts(*, request: RouteRequest, result: RouteResult) -> None:
    """Validate that the result leg list matches the route kind and order length."""
    location = "fastest_route.presentation.gui.app.flows.route_csv_export._validate_leg_counts"
    if not result.order:
        raise ValidationError(location, "Route order must not be empty.")
    if not result.legs:
        raise ValidationError(location, "Route legs must not be empty.")

    expected = (
        len(result.order) if request.route_kind == RouteKind.ROUND_TRIP else len(result.order) - 1
    )
    if expected < 1:
        raise ValidationError(location, "Route is too small to export.")
    if len(result.legs) != expected:
        raise ValidationError(location, "Route legs do not match expected leg count.")


def _build_leg_rows(*, request: RouteRequest, result: RouteResult) -> list[RouteLegCsvRow]:
    """Build typed CSV rows for each leg including cumulative totals."""
    location = "fastest_route.presentation.gui.app.flows.route_csv_export._build_leg_rows"
    _validate_leg_counts(request=request, result=result)
    try:
        trip_label = "round_trip" if request.route_kind == RouteKind.ROUND_TRIP else "path"
        cumulative = 0.0
        rows: list[RouteLegCsvRow] = []
        warnings = tuple(dict.fromkeys((*route_safety_warnings(request.mode), *result.warnings)))
        safety_warnings = "; ".join(warnings)
        order = list(result.order)
        leg_pairs: list[tuple[int, int]] = list(zip(order, order[1:], strict=False))
        if request.route_kind == RouteKind.ROUND_TRIP:
            leg_pairs.append((order[-1], order[0]))

        for idx, ((from_idx, to_idx), value) in enumerate(
            zip(leg_pairs, result.legs, strict=True), start=1
        ):
            cumulative += float(value)
            rows.append(
                RouteLegCsvRow(
                    leg_index=idx,
                    from_index=int(from_idx),
                    to_index=int(to_idx),
                    from_resolved=str(request.addresses[from_idx]),
                    to_resolved=str(request.addresses[to_idx]),
                    from_original=str(request.originals[from_idx]),
                    to_original=str(request.originals[to_idx]),
                    value=float(value),
                    cumulative=float(cumulative),
                    units=str(result.units),
                    trip=trip_label,
                    travel_mode=request.mode.value,
                    optimize_for=request.optimize_for.value,
                    safety_warnings=safety_warnings,
                )
            )
        return rows
    except ValidationError:
        raise
    except (IndexError, TypeError, ValueError) as exc:
        raise ValidationError(location, "Failed to build CSV export rows.") from exc


def export_route_csv(
    *,
    root: tk.Tk,
    request: RouteRequest | None,
    result: RouteResult | None,
    default_filename: str = "route_legs.csv",
) -> None:
    """Prompt for a CSV file path and export the per-leg breakdown of the most recent route."""
    location = "fastest_route.presentation.gui.app.flows.route_csv_export.export_route_csv"
    if not root:
        raise ValidationError(location, "root is required.")
    try:
        if request is None or result is None:
            messagebox.showwarning(
                "Export CSV",
                "No optimized route is available to export yet. Click Optimize Route first.",
                parent=root,
            )
            return

        try:
            rows = _build_leg_rows(request=request, result=result)
        except ValidationError as exc:
            messagebox.showerror("Export CSV", strip_location_prefix(str(exc)), parent=root)
            return

        path_str = filedialog.asksaveasfilename(
            parent=root,
            title="Export route legs as CSV",
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)

        fieldnames: Sequence[str] = list(rows[0].as_dict().keys())
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row.as_dict())
            messagebox.showinfo(
                "Export CSV",
                f"Exported {len(rows)} legs to:\n{path}",
                parent=root,
            )
        except OSError as exc:
            messagebox.showerror(
                "Export CSV",
                f"Failed to write CSV file.\n\n{exc}",
                parent=root,
            )
    except tk.TclError as exc:
        raise ValidationError(location, "Failed to export CSV.") from exc
