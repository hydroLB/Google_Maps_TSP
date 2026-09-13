from __future__ import annotations

import pytest

from fastest_route.presentation.gui.app.views.sections.input_section import clamp_visible_stop_count
from fastest_route.shared.errors import ValidationError


def test_clamp_visible_stop_count_clamps_to_range() -> None:
    """UI add/remove behavior should never exceed configured bounds."""
    assert clamp_visible_stop_count(min_stops=3, max_stops=7, requested=3) == 3
    assert clamp_visible_stop_count(min_stops=3, max_stops=7, requested=7) == 7
    assert clamp_visible_stop_count(min_stops=3, max_stops=7, requested=2) == 3
    assert clamp_visible_stop_count(min_stops=3, max_stops=7, requested=999) == 7


def test_clamp_visible_stop_count_rejects_invalid_constraints() -> None:
    """Invalid config should fail early with actionable messages."""
    with pytest.raises(ValidationError):
        clamp_visible_stop_count(min_stops=0, max_stops=7, requested=3)
    with pytest.raises(ValidationError):
        clamp_visible_stop_count(min_stops=4, max_stops=3, requested=4)
