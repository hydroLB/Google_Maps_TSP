# Versioning

This repository uses Semantic Versioning (`MAJOR.MINOR.PATCH`) for releases.

## SemVer Policy

- `MAJOR`: incompatible behavior or contract changes.
- `MINOR`: backward-compatible features and enhancements.
- `PATCH`: backward-compatible fixes, hardening, and maintenance updates.

## Release Tag Strategy

- Tags must be annotated as `vX.Y.Z`.
- Tag version must exactly match `pyproject.toml` `version`.
- Tags are immutable once published.
- Hotfixes are released as the next patch version (for example `v1.2.4` after `v1.2.3`).

## Label-to-Version Hints

Changelog automation resolves version bump hints from PR labels:

- `semver:major`
- `semver:minor`
- `semver:patch` (default when none is present)

These labels inform draft release notes and expected bump strategy; the final tag
version is still explicitly chosen at release time.
