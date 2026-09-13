"""Smoke-test the built wheel from a clean, isolated installation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    child_env = os.environ.copy() if env is None else env.copy()
    for variable in ("COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE"):
        child_env.pop(variable, None)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=child_env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Command failed ({result.returncode}): {' '.join(command)}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result.stdout


def _venv_executable(venv_dir: Path, name: str) -> Path:
    scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return scripts_dir / f"{name}{suffix}"


def test_start_launcher_resolves_run_script_outside_repository_cwd(tmp_path: Path) -> None:
    if os.name == "nt":
        return

    project_dir = tmp_path / "project with spaces"
    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "start", project_dir / "start")
    run_script = scripts_dir / "run.sh"
    run_script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf \'%s\\n\' "$@" > "${START_TEST_OUTPUT:?}"\n',
        encoding="utf-8",
    )
    run_script.chmod(0o755)

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    output_path = tmp_path / "launcher-output.txt"
    env = os.environ.copy()
    env["START_TEST_OUTPUT"] = str(output_path)

    _run(
        [str(project_dir / "start"), "argument with spaces"],
        cwd=outside_dir,
        env=env,
    )

    assert output_path.read_text(encoding="utf-8") == "argument with spaces\n"


def test_built_wheel_loads_packaged_config_through_both_entry_points(tmp_path: Path) -> None:
    source_config = REPO_ROOT / "TSP_GOOGLE_MAPS" / "config.toml"
    packaged_config = REPO_ROOT / "TSP_GOOGLE_MAPS" / "fastest_route" / "config" / "default.toml"
    assert packaged_config.read_bytes() == source_config.read_bytes()

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(dist_dir),
            str(REPO_ROOT),
        ],
        cwd=tmp_path,
    )
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1

    venv_dir = tmp_path / "installed"
    _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=tmp_path)
    installed_python = _venv_executable(venv_dir, "python")
    _run(
        [
            str(installed_python),
            "-m",
            "pip",
            "install",
            "--require-hashes",
            "-r",
            str(REPO_ROOT / "requirements.lock"),
        ],
        cwd=tmp_path,
    )
    _run(
        [
            str(installed_python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            str(wheels[0]),
        ],
        cwd=tmp_path,
    )

    run_dir = tmp_path / "outside-source-tree"
    run_dir.mkdir()
    isolated_env = os.environ.copy()
    for variable in (
        "FASTEST_ROUTE_CONFIG_PATH",
        "FASTEST_ROUTE_ENV",
        "PYTHONPATH",
        "GOOGLE_MAPS_API_KEY",
    ):
        isolated_env.pop(variable, None)
    isolated_env["PYTHONNOUSERSITE"] = "1"
    isolated_env["HOME"] = str(tmp_path / "home")
    isolated_env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    app_config_dir = Path(isolated_env["XDG_CONFIG_HOME"]) / "fastest_route"
    app_config_dir.mkdir(parents=True)
    (app_config_dir / ".env").write_text("FASTEST_ROUTE_ENV=local\n", encoding="utf-8")
    (run_dir / ".env").write_text("FASTEST_ROUTE_ENV=production\n", encoding="utf-8")

    import_output = _run(
        [
            str(installed_python),
            "-I",
            "-c",
            (
                "import requests; "
                "from fastest_route.infrastructure.google_maps.client import GoogleMapsClient; "
                "assert requests.Session is not None; "
                "print(GoogleMapsClient.__name__)"
            ),
        ],
        cwd=run_dir,
        env=isolated_env,
    )
    assert import_output.strip() == "GoogleMapsClient"

    module_output = _run(
        [str(installed_python), "-I", "-m", "fastest_route", "--check-config"],
        cwd=run_dir,
        env=isolated_env,
    )
    assert "Configuration OK (environment=local)" in module_output

    console_output = _run(
        [str(_venv_executable(venv_dir, "fastest-route")), "--check-config"],
        cwd=run_dir,
        env=isolated_env,
    )
    assert "Configuration OK (environment=local)" in console_output

    site_packages = Path(
        _run(
            [
                str(installed_python),
                "-I",
                "-c",
                "import sysconfig; print(sysconfig.get_paths()['purelib'])",
            ],
            cwd=run_dir,
            env=isolated_env,
        ).strip()
    )
    (site_packages / "config.toml").write_text(
        "[app]\nenvironment = 'hijacked'\n", encoding="utf-8"
    )

    config_path_output = _run(
        [
            str(installed_python),
            "-I",
            "-c",
            (
                "from fastest_route.config.loader import _default_config_path; "
                "path = _default_config_path(); "
                "assert path.name == 'default.toml' and path.is_file(); "
                "print(path)"
            ),
        ],
        cwd=run_dir,
        env=isolated_env,
    )
    assert "site-packages" in config_path_output
