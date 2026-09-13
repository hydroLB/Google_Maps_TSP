from __future__ import annotations

from types import SimpleNamespace

import pytest

from fastest_route.presentation.gui.app.controllers.autocomplete_controller import (
    AutocompleteController,
    should_display_autocomplete_results,
)


def test_input_mutation_hides_existing_popup_before_debounced_fetch() -> None:
    events: list[str] = []

    class Entry:
        value = "Boston"

        def get(self) -> str:
            return self.value

    entry = Entry()

    class Root:
        def after_cancel(self, _identifier: str) -> None:
            events.append("cancel")

        def after(self, _delay: int, _callback: object) -> str:
            events.append("schedule")
            return "new-id"

    controller = AutocompleteController.__new__(AutocompleteController)
    controller._root = Root()
    controller._config = SimpleNamespace(ui=SimpleNamespace(autocomplete_delay_ms=300))
    controller._runtime = SimpleNamespace(autocomplete_after_ids={entry: "old-id"})
    controller._request_generation = 0
    controller._scheduled_queries = {}
    controller.hide = lambda: events.append("hide")

    controller.schedule(entry)  # type: ignore[arg-type]

    assert events == ["hide", "cancel", "schedule"]

    controller.schedule(entry)  # type: ignore[arg-type]

    assert events == ["hide", "cancel", "schedule"]

    entry.value = "Boston, MA"
    controller.schedule(entry)  # type: ignore[arg-type]

    assert events == ["hide", "cancel", "schedule", "hide", "cancel", "schedule"]


def test_current_focused_autocomplete_response_is_displayable() -> None:
    assert should_display_autocomplete_results(
        expected_query="Boston",
        current_query="Boston",
        expected_generation=4,
        active_generation=4,
        entry_has_focus=True,
    )


@pytest.mark.parametrize(
    ("current_query", "active_generation", "entry_has_focus"),
    [
        ("Bos", 4, True),
        ("Boston", 5, True),
        ("Boston", 4, False),
    ],
)
def test_stale_or_unfocused_autocomplete_response_is_suppressed(
    current_query: str, active_generation: int, entry_has_focus: bool
) -> None:
    assert not should_display_autocomplete_results(
        expected_query="Boston",
        current_query=current_query,
        expected_generation=4,
        active_generation=active_generation,
        entry_has_focus=entry_has_focus,
    )
