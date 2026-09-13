from __future__ import annotations

import importlib
from types import SimpleNamespace

from fastest_route.shared.errors import ConfigError

app_main = importlib.import_module("fastest_route.entrypoint")


def test_main_logs_error_code_on_startup_failure(monkeypatch) -> None:
    """Keeps entrypoint observability consistent for operational triage."""
    calls: list[dict[str, object]] = []

    def fake_error(message: str, *, extra: dict[str, object]) -> None:
        calls.append({"message": message, "extra": extra})

    monkeypatch.setattr(
        app_main,
        "_build_dependencies",
        lambda: (_ for _ in ()).throw(ConfigError("tests.main", "config missing")),
    )
    monkeypatch.setattr(app_main, "logger", SimpleNamespace(error=fake_error))

    exit_code = app_main.main()

    assert exit_code == 1
    assert len(calls) == 1
    assert calls[0]["message"] == "Startup failed"
    assert calls[0]["extra"]["error_code"] == "E_CONFIG"
