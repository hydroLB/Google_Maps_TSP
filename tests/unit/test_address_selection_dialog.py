"""Focused headless checks for the ambiguous-address selection dialog."""

from __future__ import annotations

from fastest_route.presentation.gui.app.dialogs import address_selection_dialog


def test_address_selection_dialog_packs_google_maps_attribution(monkeypatch) -> None:
    """Provider-derived address choices carry attribution inside their modal."""
    calls: list[tuple[object, dict[str, object]]] = []
    root = object()

    class Attribution:
        def pack(self, **kwargs: object) -> None:
            calls.append((root, kwargs))

    def create_attribution(*, root: object) -> Attribution:
        calls.append((root, {}))
        return Attribution()

    monkeypatch.setattr(
        address_selection_dialog,
        "create_google_maps_attribution",
        create_attribution,
    )

    address_selection_dialog._pack_provider_attribution(root=root, row_spacing=7)

    assert calls == [(root, {}), (root, {"anchor": "e", "pady": (0, 7)})]
