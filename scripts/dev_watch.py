"""Watch GUI-related source files and restart the desktop app when changes are detected."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from types import FrameType

_STOP_REQUESTED = False


def log(level: str, message: str) -> None:
    """Emit a structured watcher log line to stderr."""
    print(f"[{level}] {message}", file=sys.stderr, flush=True)


def request_stop(signum: int, _frame: FrameType | None) -> None:
    """Mark the watch loop for graceful termination on process signals."""
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    log("INFO", f"Stop requested (signal={signum}).")


def install_signal_handlers() -> None:
    """Register termination handlers so watcher shutdown does not orphan child processes."""
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse and validate watcher CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Restart the GUI command when watched files change.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=0.75,
        help="Filesystem polling interval in seconds.",
    )
    parser.add_argument(
        "--graceful-timeout-seconds",
        type=float,
        default=4.0,
        help="Seconds to wait before force-killing the previous GUI process.",
    )
    parser.add_argument(
        "--watch-root",
        action="append",
        required=True,
        help="File or directory to watch. Can be repeated.",
    )
    parser.add_argument(
        "--watch-extension",
        action="append",
        default=[],
        help="File extension suffix to watch (example: .py). Can be repeated.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute. Place '--' before the command.",
    )
    parsed = parser.parse_args(list(argv))

    if parsed.poll_interval_seconds <= 0:
        parser.error("--poll-interval-seconds must be > 0.")
    if parsed.graceful_timeout_seconds <= 0:
        parser.error("--graceful-timeout-seconds must be > 0.")
    if parsed.command and parsed.command[0] == "--":
        parsed.command = parsed.command[1:]
    if not parsed.command:
        parser.error("Missing command to run. Add '-- <command>'.")
    return parsed


def normalize_extensions(values: Sequence[str]) -> tuple[str, ...]:
    """Normalize extension values to lowercase dot-prefixed suffix tokens."""
    location = "scripts.dev_watch.normalize_extensions"
    normalized: list[str] = []
    for value in values:
        candidate = value.strip().lower()
        if not candidate:
            continue
        if not candidate.startswith("."):
            candidate = f".{candidate}"
        normalized.append(candidate)
    unique = tuple(sorted(set(normalized)))
    if not unique:
        raise RuntimeError(f"{location}: No valid watch extensions were provided.")
    return unique


def resolve_watch_roots(values: Sequence[str], cwd: Path) -> tuple[Path, ...]:
    """
    Resolve and validate absolute watch-root paths from CLI values.

    Fails fast with clear path errors before starting the child process loop.
    """
    location = "scripts.dev_watch.resolve_watch_roots"
    roots: list[Path] = []
    for raw_value in values:
        candidate = Path(raw_value).expanduser()
        if not candidate.is_absolute():
            candidate = (cwd / candidate).resolve()
        if not candidate.exists():
            raise RuntimeError(
                f"{location}: Watch root does not exist: {candidate}",
            )
        roots.append(candidate)
    unique = tuple(sorted(set(roots)))
    if not unique:
        raise RuntimeError(f"{location}: At least one watch root is required.")
    return unique


def matches_extension(path: Path, extensions: Sequence[str]) -> bool:
    """Determine whether a file path matches configured extension suffixes."""
    file_name = path.name.lower()
    return any(file_name.endswith(extension) for extension in extensions)


def iter_matching_files(root: Path, extensions: Sequence[str]) -> Iterable[Path]:
    """Enumerate watched files under a root path using extension filtering."""
    location = "scripts.dev_watch.iter_matching_files"
    try:
        if root.is_file():
            if matches_extension(root, extensions):
                yield root
            return
        for candidate in root.rglob("*"):
            if candidate.is_file() and matches_extension(candidate, extensions):
                yield candidate
    except OSError as exc:
        raise RuntimeError(
            f"{location}: Failed while scanning watch root {root}",
        ) from exc


def build_snapshot(roots: Sequence[Path], extensions: Sequence[str]) -> dict[Path, int]:
    """Build a filesystem state snapshot keyed by file path and modification time."""
    location = "scripts.dev_watch.build_snapshot"
    snapshot: dict[Path, int] = {}
    for root in roots:
        for candidate in iter_matching_files(root, extensions):
            try:
                snapshot[candidate] = candidate.stat().st_mtime_ns
            except FileNotFoundError:
                # A file can be deleted between discovery and stat; skip and rely on snapshot diff.
                continue
            except OSError as exc:
                raise RuntimeError(
                    f"{location}: Failed to read metadata for {candidate}",
                ) from exc
    return snapshot


def detect_changes(previous: dict[Path, int], current: dict[Path, int]) -> list[Path]:
    """Compute changed file paths between two snapshots."""
    changed = [
        path for path in set(previous) | set(current) if previous.get(path) != current.get(path)
    ]
    return sorted(changed)


def to_display_path(path: Path, cwd: Path) -> str:
    """Convert an absolute path into a concise display path for logs."""
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def start_command(command: Sequence[str], cwd: Path) -> subprocess.Popen[bytes]:
    """
    Start the watched GUI command in a new process session.

    Process-session isolation allows reliable termination of any child subtree.
    """
    location = "scripts.dev_watch.start_command"
    try:
        return subprocess.Popen(
            list(command),
            cwd=str(cwd),
            start_new_session=True,
        )
    except OSError as exc:
        raise RuntimeError(
            f"{location}: Failed to start command: {' '.join(command)}",
        ) from exc


def stop_command(process: subprocess.Popen[bytes], graceful_timeout_seconds: float) -> None:
    """Stop a running command process with graceful shutdown before force kill."""
    location = "scripts.dev_watch.stop_command"
    if process.poll() is not None:
        return

    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    except OSError as exc:
        raise RuntimeError(
            f"{location}: Failed to send graceful termination signal.",
        ) from exc

    try:
        process.wait(timeout=graceful_timeout_seconds)
        return
    except subprocess.TimeoutExpired:
        pass

    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        return
    except OSError as exc:
        raise RuntimeError(
            f"{location}: Failed to send force-kill signal.",
        ) from exc
    process.wait(timeout=graceful_timeout_seconds)


def run_watch_loop(
    *,
    command: Sequence[str],
    cwd: Path,
    roots: Sequence[Path],
    extensions: Sequence[str],
    poll_interval_seconds: float,
    graceful_timeout_seconds: float,
) -> int:
    """Run the main watch loop and restart the command on file changes."""
    initial_snapshot = build_snapshot(roots, extensions)
    display_roots = ", ".join(to_display_path(root, cwd) for root in roots)
    log("INFO", f"Watching roots: {display_roots}")
    log("INFO", f"Watching suffixes: {', '.join(extensions)}")
    log("INFO", f"Starting command: {' '.join(command)}")

    process: subprocess.Popen[bytes] | None = start_command(command, cwd)
    previous_snapshot = initial_snapshot

    while True:
        if _STOP_REQUESTED:
            if process is not None:
                stop_command(process, graceful_timeout_seconds)
            return 0

        if process is not None:
            exit_code = process.poll()
            if exit_code is not None:
                if exit_code == 0:
                    log("INFO", "GUI process exited cleanly. Stopping watcher.")
                    return 0
                log(
                    "WARN",
                    f"GUI process exited with code {exit_code}. Waiting for file changes to restart.",
                )
                process = None

        current_snapshot = build_snapshot(roots, extensions)
        changed_paths = detect_changes(previous_snapshot, current_snapshot)
        if changed_paths:
            display_changes = ", ".join(to_display_path(path, cwd) for path in changed_paths[:5])
            if len(changed_paths) > 5:
                display_changes = f"{display_changes}, ... ({len(changed_paths)} files)"
            log("INFO", f"Detected changes: {display_changes}")
            if process is not None:
                stop_command(process, graceful_timeout_seconds)
            process = start_command(command, cwd)
        previous_snapshot = current_snapshot
        time.sleep(poll_interval_seconds)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse watcher configuration and execute the live-reload loop."""
    location = "scripts.dev_watch.main"
    parsed = parse_args(sys.argv[1:] if argv is None else argv)
    cwd = Path.cwd()
    install_signal_handlers()

    raw_extensions = parsed.watch_extension or [".py", ".toml", ".env"]
    try:
        extensions = normalize_extensions(raw_extensions)
        roots = resolve_watch_roots(parsed.watch_root, cwd)
        return run_watch_loop(
            command=parsed.command,
            cwd=cwd,
            roots=roots,
            extensions=extensions,
            poll_interval_seconds=parsed.poll_interval_seconds,
            graceful_timeout_seconds=parsed.graceful_timeout_seconds,
        )
    except RuntimeError as exc:
        log("ERROR", f"{location}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
