from __future__ import annotations

import importlib
from pathlib import Path

import pytest

dev_watch = importlib.import_module("scripts.dev_watch")


def test_parse_args_strips_command_separator() -> None:
    """Ensures shell wrappers can pass child command tokens reliably."""
    parsed = dev_watch.parse_args(
        [
            "--watch-root",
            "TSP_GOOGLE_MAPS",
            "--watch-extension",
            ".py",
            "--",
            "python",
            "TSP_GOOGLE_MAPS/main.py",
        ],
    )

    assert parsed.command == ["python", "TSP_GOOGLE_MAPS/main.py"]


def test_normalize_extensions_accepts_dotless_values() -> None:
    """Prevents config formatting differences from silently disabling file matching."""
    normalized = dev_watch.normalize_extensions(["py", ".TOML", ".env"])
    assert normalized == (".env", ".py", ".toml")


def test_build_snapshot_filters_files_by_suffix(tmp_path: Path) -> None:
    """Keeps restarts focused on relevant GUI source/config changes."""
    python_file = tmp_path / "view.py"
    python_file.write_text("print('ok')\n", encoding="utf-8")

    env_file = tmp_path / ".env"
    env_file.write_text("FASTEST_ROUTE_ENV=dev\n", encoding="utf-8")

    ignored_file = tmp_path / "notes.txt"
    ignored_file.write_text("ignore me\n", encoding="utf-8")

    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested_python = nested_dir / "layout.py"
    nested_python.write_text("print('nested')\n", encoding="utf-8")

    snapshot = dev_watch.build_snapshot(
        roots=(tmp_path,),
        extensions=(".py", ".env"),
    )

    assert python_file in snapshot
    assert env_file in snapshot
    assert nested_python in snapshot
    assert ignored_file not in snapshot


def test_detect_changes_reports_add_modify_and_remove() -> None:
    """Ensures watcher restart triggers remain accurate across all filesystem delta types."""
    file_a = Path("a.py")
    file_b = Path("b.py")
    file_c = Path("c.py")

    previous = {file_a: 1, file_b: 1}
    current = {file_a: 2, file_c: 1}

    assert dev_watch.detect_changes(previous, current) == [file_a, file_b, file_c]


def test_resolve_watch_roots_rejects_missing_path(tmp_path: Path) -> None:
    """Keeps watch mode failure messages immediate and actionable."""
    missing_path = tmp_path / "does-not-exist"
    with pytest.raises(RuntimeError, match="Watch root does not exist"):
        dev_watch.resolve_watch_roots([str(missing_path)], cwd=tmp_path)
