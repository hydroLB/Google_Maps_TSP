# Contributor Bootstrap Validation Record

## Purpose

Record repeatable evidence that the documented bootstrap and complete local quality gate run
without manual tool installation beyond the project bootstrap.

## Environment

- Date: `2026-08-24`
- Platform: macOS (Apple Silicon)
- Python: `3.11.15`, matching `.python-version`
- Method: current deliverable validated through a temporary Git index so every intended file was
  treated as tracked while the contributor's real staging area remained untouched.

## Commands Executed

```bash
make setup
make check
```

## Result Summary

- `make setup`: success
- `make check`/`scripts/check.sh`: success
- Ruff format and lint: success across 181 files
- Strict mypy: success across 140 source files
- Tests: `408 passed`
- Configured non-presentation branch coverage: `90.70%` with the `90%` gate satisfied;
  `fastest_route.presentation` is outside that aggregate percentage and has targeted tests
- Runtime and development dependency audits: no known vulnerabilities
- Source and wheel builds: success from the hash-locked environment
- Distribution smoke: runtime dependencies installed from the hash-checked runtime lock, then the
  wheel installed with `--no-deps` and without project-source leakage; both packaged entry points,
  stable-path `.env` loading, and embedded config resolution succeeded
- Benchmark smoke: machine-readable JSON artifact produced

## Notes

- This record validates the local onboarding flow under the stated environment. CI is configured
  to repeat the platform-neutral gates on Ubuntu and add full-history gitleaks scanning.
- Real Tk widget behavior was smoke-checked manually on the stated macOS host. The automated E2E
  test is service-level and does not open a GUI; native Windows behavior remains unverified.
- If bootstrap or checks change, this document should be refreshed.
