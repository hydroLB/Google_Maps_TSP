"""Support ``python -m fastest_route``."""

from __future__ import annotations

from fastest_route.entrypoint import cli

if __name__ == "__main__":
    raise SystemExit(cli())
