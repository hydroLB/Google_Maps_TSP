"""
Unit tests for repository hygiene guard behavior.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _create_minimal_hygiene_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

    required_files = {
        ".editorconfig": "",
        ".env.example": "GOOGLE_MAPS_API_KEY=\n",
        ".githooks/pre-commit": "#!/usr/bin/env bash\n",
        ".githooks/pre-push": "#!/usr/bin/env bash\n",
        ".gitattributes": "",
        ".github/workflows/ci.yml": "name: ci\n",
        ".gitignore": "",
        ".pre-commit-config.yaml": "",
        ".python-version": "3.11\n",
        "Makefile": "",
        "README.md": "# Test\n",
        "SECURITY.md": "# Security\n",
        "gitleaks.toml": "",
        "pyproject.toml": "",
        "requirements.lock": "",
        "requirements-dev.lock": "",
        "scripts/bootstrap_venv.sh": "#!/usr/bin/env bash\n",
        "scripts/check.sh": "#!/usr/bin/env bash\n",
        "TSP_GOOGLE_MAPS/config.toml": '[app]\nenvironment = "test"\n',
        "TSP_GOOGLE_MAPS/fastest_route/config/default.toml": ('[app]\nenvironment = "test"\n'),
        "TSP_GOOGLE_MAPS/fastest_route/__main__.py": "",
        "TSP_GOOGLE_MAPS/fastest_route/shared/__init__.py": "",
    }
    for relative_path, text in required_files.items():
        _write(repo / relative_path, text)

    shutil.copy(ROOT / "scripts/repo_hygiene.sh", repo / "scripts/repo_hygiene.sh")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    return repo


def test_repo_hygiene_accepts_standard_dunder_modules(tmp_path: Path) -> None:
    repo = _create_minimal_hygiene_repo(tmp_path)
    subprocess_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COV_CORE_") and key != "COVERAGE_PROCESS_START"
    }
    subprocess_env["FASTEST_ROUTE_PYTHON"] = sys.executable

    result = subprocess.run(
        ["bash", "scripts/repo_hygiene.sh"],
        cwd=repo,
        env=subprocess_env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_repo_hygiene_rejects_tracked_duplicate_copy_artifacts(tmp_path: Path) -> None:
    repo = _create_minimal_hygiene_repo(tmp_path)
    _write(repo / "README 2.md", "# Copy\n")
    subprocess.run(
        ["git", "add", "README 2.md"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        ["bash", "scripts/repo_hygiene.sh"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Tracked duplicate copy artifacts are not allowed" in result.stderr
    assert "README 2.md (canonical: README.md)" in result.stderr


def test_repo_hygiene_rejects_packaged_config_drift(tmp_path: Path) -> None:
    repo = _create_minimal_hygiene_repo(tmp_path)
    _write(
        repo / "TSP_GOOGLE_MAPS/fastest_route/config/default.toml",
        '[app]\nenvironment = "production"\n',
    )
    subprocess.run(
        ["git", "add", "TSP_GOOGLE_MAPS/fastest_route/config/default.toml"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        ["bash", "scripts/repo_hygiene.sh"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Source and packaged default configuration files have drifted" in result.stderr
