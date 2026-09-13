from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastest_route.presentation.gui.app.flows import guided_entry as guided_entry_flow
from fastest_route.presentation.gui.app.flows.guided_entry import apply_guided_entry_lines
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from fastest_route.config.registry import AppConfig


class FakeEntry:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self.events = events
        self.value = "old"

    def delete(self, _first: int, _last: str) -> None:
        self.events.append(("delete", self.value))
        self.value = ""

    def insert(self, _index: int, value: str) -> None:
        self.events.append(("insert", value))
        self.value = value


def test_apply_guided_entry_expands_before_populating() -> None:
    events: list[tuple[str, object]] = []
    entries = [FakeEntry(events) for _ in range(5)]

    apply_guided_entry_lines(
        lines=["A", "B", "C", "D"],
        stop_entries=entries,  # type: ignore[arg-type]
        set_visible_stops=lambda count: events.append(("visible", count)),
        update_stop_counter=lambda: events.append(("counter", None)),
        clear_status_labels=lambda: events.append(("clear-status", None)),
        schedule_status_check=lambda idx: events.append(("status", idx)),
    )

    assert events[0] == ("visible", 4)
    assert [entry.value for entry in entries] == ["A", "B", "C", "D", "old"]
    assert ("clear-status", None) in events
    assert events[-4:] == [("status", 1), ("status", 2), ("status", 3), ("status", 4)]


def test_apply_guided_entry_rejects_more_lines_than_fields() -> None:
    entries = [FakeEntry([]) for _ in range(3)]

    with pytest.raises(ValidationError, match="exceed the available stop fields"):
        apply_guided_entry_lines(
            lines=["A", "B", "C", "D"],
            stop_entries=entries,  # type: ignore[arg-type]
            set_visible_stops=lambda _count: None,
            update_stop_counter=lambda: None,
            clear_status_labels=lambda: None,
            schedule_status_check=lambda _idx: None,
        )


def test_run_guided_entry_applies_dialog_result(
    monkeypatch: pytest.MonkeyPatch, app_config: AppConfig
) -> None:
    events: list[tuple[str, object]] = []
    entries = [FakeEntry(events) for _ in range(app_config.ui.max_stops)]
    monkeypatch.setattr(
        guided_entry_flow,
        "prompt_guided_entry",
        lambda **_kwargs: ["A", "B", "C", "D"],
    )

    guided_entry_flow.run_guided_entry(
        root=object(),  # type: ignore[arg-type]
        config=app_config,
        stop_entries=entries,  # type: ignore[arg-type]
        set_visible_stops=lambda count: events.append(("visible", count)),
        update_stop_counter=lambda: events.append(("counter", None)),
        clear_status_labels=lambda: events.append(("clear-status", None)),
        schedule_status_check=lambda idx: events.append(("status", idx)),
    )

    assert [entry.value for entry in entries[:4]] == ["A", "B", "C", "D"]
    assert events[0] == ("visible", 4)
    assert ("clear-status", None) in events
    assert [("status", idx) for idx in range(1, 5)] == events[-4:]
