"""Source-tree launcher retained for backwards-compatible local execution."""

from __future__ import annotations

import sys

from fastest_route.entrypoint import cli, main

__all__ = ["cli", "main"]


if __name__ == "__main__":
    sys.exit(cli())
