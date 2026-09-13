from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from fastest_route.config.dotenv import load_env_file, resolve_env_file_path
from fastest_route.infrastructure.envfile import upsert_env_var
from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from pathlib import Path


def test_load_env_file_preserves_explicit_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        '# comment\nGOOGLE_MAPS_API_KEY="from file"\nFASTEST_ROUTE_ENV=local\nHTTPS_PROXY=https://attacker.invalid\nFASTEST_ROUTE_CONFIG_PATH=/tmp/untrusted.toml\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "from-process")
    monkeypatch.delenv("FASTEST_ROUTE_ENV", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("FASTEST_ROUTE_CONFIG_PATH", raising=False)

    load_env_file(env_path)

    assert os.environ["GOOGLE_MAPS_API_KEY"] == "from-process"
    assert os.environ["FASTEST_ROUTE_ENV"] == "local"
    assert "HTTPS_PROXY" not in os.environ
    assert "FASTEST_ROUTE_CONFIG_PATH" not in os.environ


def test_load_env_file_rejects_syntax_without_exposing_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("not-an-assignment\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="line 1"):
        load_env_file(env_path)


def test_resolve_env_file_path_uses_repository_root_for_source_checkout(tmp_path: Path) -> None:
    package_root = tmp_path / "TSP_GOOGLE_MAPS" / "fastest_route"
    module_path = package_root / "config" / "dotenv.py"
    module_path.parent.mkdir(parents=True)
    (package_root.parent / "config.toml").write_text("[app]\n", encoding="utf-8")

    resolved = resolve_env_file_path(
        module_path=module_path,
        environ={"XDG_CONFIG_HOME": str(tmp_path / "ignored")},
        home=tmp_path / "home",
    )

    assert resolved == tmp_path / ".env"


def test_resolve_env_file_path_uses_xdg_for_installed_package(tmp_path: Path) -> None:
    module_path = tmp_path / "site-packages" / "fastest_route" / "config" / "dotenv.py"
    xdg_home = tmp_path / "xdg"
    (module_path.parents[2] / "config.toml").parent.mkdir(parents=True)
    (module_path.parents[2] / "config.toml").write_text("[app]\n", encoding="utf-8")

    resolved = resolve_env_file_path(
        module_path=module_path,
        environ={"XDG_CONFIG_HOME": str(xdg_home)},
        home=tmp_path / "home",
    )

    assert resolved == xdg_home / "fastest_route" / ".env"


def test_resolve_env_file_path_ignores_relative_xdg_home(tmp_path: Path) -> None:
    module_path = tmp_path / "site-packages" / "fastest_route" / "config" / "dotenv.py"
    home = tmp_path / "home"

    resolved = resolve_env_file_path(
        module_path=module_path,
        environ={"XDG_CONFIG_HOME": "relative/path"},
        home=home,
    )

    assert resolved == home / ".config" / "fastest_route" / ".env"


def test_load_env_file_secures_existing_file(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("FASTEST_ROUTE_ENV=test\n", encoding="utf-8")
    env_path.chmod(0o644)

    load_env_file(env_path)

    assert env_path.stat().st_mode & 0o777 == 0o600


def test_upsert_env_var_creates_file_and_writes_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    upsert_env_var(env_path, "GOOGLE_MAPS_API_KEY", "abc123")
    assert env_path.exists()
    assert env_path.read_text() == "GOOGLE_MAPS_API_KEY=abc123\n"


def test_upsert_env_var_updates_existing_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("# comment\nGOOGLE_MAPS_API_KEY=old\nFASTEST_ROUTE_ENV=dev\n")
    env_path.chmod(0o644)
    upsert_env_var(env_path, "GOOGLE_MAPS_API_KEY", "new")
    assert env_path.read_text() == "# comment\nGOOGLE_MAPS_API_KEY=new\nFASTEST_ROUTE_ENV=dev\n"
    assert env_path.stat().st_mode & 0o777 == 0o600


def test_upsert_env_var_rejects_invalid_key(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    with pytest.raises(ValidationError):
        upsert_env_var(env_path, "NOT A KEY", "x")
