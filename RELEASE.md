# Release Process

This repository supports automated release publishing from CI.

## Prerequisites

1. Ensure `pyproject.toml` version is updated to the intended release.
2. Ensure `make check` passes on `main`.
3. Confirm release notes draft in GitHub is current (`changelog-automation` workflow).

## Changelog Automation

- Workflow: `.github/workflows/changelog-automation.yml`
- Engine: Release Drafter (`.github/release-drafter.yml`)
- Trigger: push to `main` and manual `workflow_dispatch`

This workflow keeps a draft release/changelog updated using merged PR metadata.

## Publish Release from CI

1. Create and push a SemVer tag:
   - `git tag -a vX.Y.Z -m "vX.Y.Z"`
   - `git push origin vX.Y.Z`
2. CI workflow `.github/workflows/release.yml` runs automatically.
3. Workflow steps:
   - validates tag format `vX.Y.Z`
   - requires an annotated tag whose commit is contained in `main`
   - validates tag version matches `pyproject.toml`
   - runs the same full quality gate used by pull requests
   - scans the full history for leaked secrets and verifies checks do not mutate tracked files
   - uploads the verified wheel and source distribution
   - publishes a GitHub release with generated notes and SHA-256 checksums

## Manual CI Run

The `release` workflow supports `workflow_dispatch` for validation/build checks.
Publishing only occurs on valid tag refs.
