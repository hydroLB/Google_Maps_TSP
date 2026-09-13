"""Widget-independent coverage for the offline demo window prefill."""

from __future__ import annotations

from types import SimpleNamespace

from fastest_route.infrastructure.demo.maps_client import DEMO_PREFILL_ADDRESSES
from fastest_route.presentation.gui.app.window import _prefill_offline_demo


class _Entry:
    def __init__(self) -> None:
        self.value = "old"

    def delete(self, _first: int, _last: object) -> None:
        self.value = ""

    def insert(self, _index: int, value: str) -> None:
        self.value = value


def test_offline_demo_prefills_exactly_three_visible_stops() -> None:
    visible_counts: list[int] = []
    start = _Entry()
    stops = [_Entry() for _ in range(7)]
    end = _Entry()
    widgets = SimpleNamespace(
        stops=SimpleNamespace(
            start_entry=start,
            stop_entries=stops,
            end_entry=end,
            set_visible_stops=visible_counts.append,
        )
    )

    _prefill_offline_demo(widgets)

    assert visible_counts == [3]
    assert [start.value, *(entry.value for entry in stops[:3]), end.value] == list(
        DEMO_PREFILL_ADDRESSES
    )
    assert all(entry.value == "old" for entry in stops[3:])
