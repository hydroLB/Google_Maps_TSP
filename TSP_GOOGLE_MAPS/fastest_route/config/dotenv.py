"""Resolve and safely load the application's private ``.env`` configuration."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from fastest_route.shared.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping

_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SUPPORTED_ENV_KEYS = frozenset(
    {
        "FASTEST_ROUTE_ENV",
        "FASTEST_ROUTE_LOG_LEVEL",
        "GOOGLE_MAPS_API_KEY",
    }
)


def resolve_env_file_path(
    *,
    module_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return one stable credential path for source and installed launches.

    Source checkouts use the repository-root ``.env``. Installed wheels use
    ``$XDG_CONFIG_HOME/fastest_route/.env`` when XDG_CONFIG_HOME is an absolute path, or
    ``~/.config/fastest_route/.env`` otherwise. The launch directory never influences the path.

    ``module_path``, ``environ``, and ``home`` are explicit test seams; callers normally omit them.
    """

    location = "fastest_route.config.dotenv.resolve_env_file_path"
    candidate = (module_path or Path(__file__)).expanduser().resolve()
    try:
        package_root = candidate.parents[1]
    except IndexError as exc:
        raise ValidationError(
            location, "Unable to resolve the application credential path."
        ) from exc

    source_config = package_root.parent / "config.toml"
    if (
        package_root.name == "fastest_route"
        and package_root.parent.name == "TSP_GOOGLE_MAPS"
        and source_config.is_file()
    ):
        return package_root.parent.parent / ".env"

    environment = os.environ if environ is None else environ
    xdg_raw = environment.get("XDG_CONFIG_HOME", "").strip()
    if xdg_raw:
        xdg_path = Path(xdg_raw).expanduser()
        if xdg_path.is_absolute():
            return xdg_path / "fastest_route" / ".env"
    home_path = (Path.home() if home is None else home).expanduser()
    return home_path / ".config" / "fastest_route" / ".env"


def load_env_file(env_path: Path) -> None:
    """Load ``KEY=VALUE`` pairs without executing shell syntax.

    Existing non-empty process variables win over file values. This keeps explicit CI and shell
    configuration authoritative while making credentials saved by the desktop UI effective on the
    next packaged launch.
    """

    location = "fastest_route.config.dotenv.load_env_file"
    if not isinstance(env_path, Path):
        raise ValidationError(location, "env_path must be a pathlib.Path.")
    env_path = env_path.expanduser()
    if not env_path.exists():
        return
    try:
        os.chmod(env_path, 0o600)
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(location, f"Failed to secure or read env file '{env_path}'.") from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValidationError(location, f"Invalid .env syntax at line {line_number}.")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _ENV_KEY_RE.fullmatch(key):
            raise ValidationError(location, f"Invalid .env key at line {line_number}.")
        if key not in _SUPPORTED_ENV_KEYS:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
            if raw_value.strip().startswith('"'):
                value = value.replace(r"\"", '"').replace(r"\\", "\\")
        if not os.environ.get(key):
            os.environ[key] = value
