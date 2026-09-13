"""Atomic, private-by-default persistence helpers for local JSON caches."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path


def write_json_atomically(path: Path, payload: object) -> None:
    """Replace ``path`` atomically after flushing a complete JSON document to disk.

    Cache writes use a same-directory temporary file so ``os.replace`` cannot expose a
    partially written document, even if the application is interrupted during shutdown.
    The file is restricted to the current user on POSIX systems because cache keys and
    optional geocode values may still be sensitive.
    """

    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        with suppress(OSError):
            os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink()
