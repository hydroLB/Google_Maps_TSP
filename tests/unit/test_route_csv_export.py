from __future__ import annotations

import csv
from typing import TYPE_CHECKING

import pytest

from fastest_route.presentation.gui.app.flows.route_csv_export import (
    _build_leg_rows,
    export_route_csv,
)
from fastest_route.shared.errors import ValidationError
from fastest_route.shared.types import (
    NON_MOTORIZED_ROUTE_WARNING,
    OptimizeFor,
    RouteKind,
    RouteRequest,
    RouteResult,
    TravelMode,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_build_leg_rows_path_maps_pairs_and_cumulative() -> None:
    """Export relies on the same mapping logic as UI leg breakdowns; mismatches would mislead users."""
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["a", "b", "c"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    result = RouteResult(order=[0, 2, 1], total=12.0, units="min", legs=[5.0, 7.0])
    rows = _build_leg_rows(request=request, result=result)
    assert [r.leg_index for r in rows] == [1, 2]
    assert [(r.from_resolved, r.to_resolved) for r in rows] == [("A", "C"), ("C", "B")]
    assert [r.cumulative for r in rows] == [5.0, 12.0]
    assert rows[0].units == "min"
    assert rows[0].trip == "path"


def test_build_leg_rows_round_trip_includes_return_leg() -> None:
    """Return-to-start workflows are common and must export the final closing leg."""
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["a", "b", "c"],
        mode=TravelMode.WALKING,
        optimize_for=OptimizeFor.DISTANCE,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.ROUND_TRIP,
    )
    result = RouteResult(order=[0, 2, 1], total=60.0, units="km", legs=[10.0, 20.0, 30.0])
    rows = _build_leg_rows(request=request, result=result)
    assert len(rows) == 3
    assert [(r.from_resolved, r.to_resolved) for r in rows] == [("A", "C"), ("C", "B"), ("B", "A")]
    assert [r.cumulative for r in rows] == [10.0, 30.0, 60.0]
    assert rows[-1].trip == "round_trip"
    assert rows[-1].safety_warnings == NON_MOTORIZED_ROUTE_WARNING


def test_build_leg_rows_rejects_leg_count_mismatch() -> None:
    """Prevents silently writing incorrect CSV mappings when caches or computations are inconsistent."""
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["A", "B", "C"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    result = RouteResult(order=[0, 1, 2], total=12.0, units="min", legs=[12.0])
    with pytest.raises(ValidationError):
        _build_leg_rows(request=request, result=result)


def test_export_route_csv_writes_expected_columns(tmp_path: Path, monkeypatch) -> None:
    """Ensures the exported artifact is useful in spreadsheets and downstream tools."""
    request = RouteRequest(
        addresses=["A", "B", "C"],
        originals=["a", "b", "c"],
        mode=TravelMode.DRIVING,
        optimize_for=OptimizeFor.TIME,
        has_start=False,
        has_end=False,
        route_kind=RouteKind.PATH,
    )
    result = RouteResult(order=[0, 1, 2], total=12.0, units="min", legs=[5.0, 7.0])
    out_path = tmp_path / "export.csv"

    from fastest_route.presentation.gui.app.flows import route_csv_export as module

    monkeypatch.setattr(
        module.filedialog,
        "asksaveasfilename",
        lambda **_kwargs: str(out_path),
    )
    monkeypatch.setattr(module.messagebox, "showwarning", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.messagebox, "showerror", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.messagebox, "showinfo", lambda *_args, **_kwargs: None)
    export_route_csv(root=object(), request=request, result=result)

    assert out_path.exists()
    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames is not None
        assert "from_resolved" in reader.fieldnames
        assert "to_resolved" in reader.fieldnames
        assert "cumulative" in reader.fieldnames
        assert len(rows) == 2
