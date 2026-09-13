"""Safe helpers for reading and updating local .env files."""

from __future__ import annotations

import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path

from fastest_route.shared.errors import ValidationError

_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def upsert_env_var(env_path: Path, key: str, value: str) -> None:
    """Atomically insert or update a ``KEY=VALUE`` entry in an environment file."""
    location = "fastest_route.infrastructure.envfile.upsert_env_var"
    if not isinstance(env_path, Path):
        raise ValidationError(location, "env_path must be a pathlib.Path.")
    if not isinstance(key, str) or not _ENV_KEY_RE.match(key):
        raise ValidationError(location, "key must be a valid environment variable name.")
    if not isinstance(value, str):
        raise ValidationError(location, "value must be a string.")
    if "\n" in value or "\r" in value:
        raise ValidationError(location, "value must not contain newlines.")

    env_path = env_path.expanduser()
    try:
        env_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise ValidationError(
            location, f"Failed to create env directory '{env_path.parent}'."
        ) from exc

    try:
        original = env_path.read_text() if env_path.exists() else ""
    except OSError as exc:
        raise ValidationError(location, f"Failed to read env file '{env_path}'.") from exc

    lines = original.splitlines(keepends=True)
    key_prefix = f"{key}="

    def format_value(raw: str) -> str:
        """Quote an environment value only when its contents require it."""
        if raw == "":
            return ""
        if re.search(r"[\\s#]", raw) is None and '"' not in raw and "'" not in raw:
            return raw
        escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    rendered = f"{key_prefix}{format_value(value)}\n"
    updated_lines: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith(key_prefix):
            if not replaced:
                updated_lines.append(rendered)
                replaced = True
            continue
        updated_lines.append(line)
    if not replaced:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines[-1] = f"{updated_lines[-1]}\n"
        updated_lines.append(rendered)

    new_content = "".join(updated_lines)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, dir=str(env_path.parent)
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(new_content)
        os.replace(tmp_path, env_path)
        tmp_path = None
        if not env_path.exists():
            raise ValidationError(location, f"Failed to write env file '{env_path}'.")
        os.chmod(env_path, 0o600)
    except ValidationError:
        raise
    except OSError as exc:
        raise ValidationError(location, f"Failed to write env file '{env_path}'.") from exc
    finally:
        if tmp_path is not None:
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)
