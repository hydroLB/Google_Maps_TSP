# Runbook: Startup Failure

## Scope

Use this runbook when the app fails during bootstrap or does not open the GUI
after `make dev`.

## Symptoms

- `make dev` exits non-zero.
- `python TSP_GOOGLE_MAPS/main.py` exits before window creation.
- Errors reference missing modules, invalid config, or Tk runtime issues.

## Immediate Triage

1. Confirm runtime and environment:
   - `python --version`
   - `make setup`
2. Run full deterministic gate:
   - `make check`
3. Capture startup error directly:
   - `./.venv/bin/python TSP_GOOGLE_MAPS/main.py`
4. Verify the credential file for the launch mode is present, without printing its contents:
   - Source checkout: `ls -la .env`
   - Installed wheel: `ls -la "${XDG_CONFIG_HOME:-$HOME/.config}/fastest_route/.env"`

## Debugging Steps

1. Config path and validation checks:
   - `echo "$FASTEST_ROUTE_CONFIG_PATH"`
   - `PYTHONPATH=TSP_GOOGLE_MAPS ./.venv/bin/python -m fastest_route --check-config`
   - Remember that `FASTEST_ROUTE_CONFIG_PATH` is a process-only override. Values placed in
     `.env` are ignored intentionally.
2. GUI dependency checks:
   - `./.venv/bin/python -c "import tkinter; print('tk ok')"`
3. Dependency integrity checks:
   - `./.venv/bin/pip check`
4. Log context checks:
   - Set `FASTEST_ROUTE_LOG_LEVEL=DEBUG` and rerun startup command.

## Mitigations

1. Recreate virtual environment:
   - `rm -rf .venv && make setup`
2. Restore baseline env file:
   - Source checkout: back up the existing file, then run `cp .env.example .env` from the
     repository root.
   - Installed wheel: use the in-app API-key action to recreate the stable user credential file at
     `${XDG_CONFIG_HOME:-$HOME/.config}/fastest_route/.env`.
3. Remove stale runtime overrides:
   - `unset FASTEST_ROUTE_CONFIG_PATH FASTEST_ROUTE_ENV FASTEST_ROUTE_LOG_LEVEL`

## Rollback Procedure

Use rollback if a mitigation introduces new failures.

1. Preserve and remove a suspect env file from the next launch:
   - Source checkout: `mv .env .env.startup-backup`
   - Installed wheel:
     `mv "${XDG_CONFIG_HOME:-$HOME/.config}/fastest_route/.env" "${XDG_CONFIG_HOME:-$HOME/.config}/fastest_route/.env.startup-backup"`
   - Do not use `git checkout` for `.env`: it is intentionally untracked. Restore a tracked
     `TSP_GOOGLE_MAPS/config.toml` only after preserving any intentional local edits.
2. Reinstall pinned baseline:
   - `make setup`
3. Validate baseline health:
   - `make check`
4. Return to last known-good commit if needed:
   - `git checkout <known_good_commit>`

## Exit Criteria

- `make dev` launches successfully.
- `make check` passes.
- Incident note includes root cause and exact fix.
