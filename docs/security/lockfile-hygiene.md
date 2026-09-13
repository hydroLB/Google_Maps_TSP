# Lockfile Hygiene Policy

## Purpose

This repository separates human-maintained direct requirements from generated,
hash-checked transitive locks.

## Policy Rules

1. Direct runtime and development dependencies remain reviewable in:
   - `requirements.txt`
   - `requirements-dev.txt`
2. Complete transitive dependency graphs are generated into:
   - `requirements.lock`
   - `requirements-dev.lock`
3. Every direct pin must appear at the same version in its corresponding lock.
4. Every locked distribution must be exactly pinned and include a SHA-256 artifact hash.
5. The runtime lock must be an identical subset of the development lock.
6. CI and local quality gates fail on direct-pin drift, cross-lock drift, unpinned entries, or
   missing hashes.

## Enforcement

- Local:
  - `./scripts/lockfile_hygiene.sh`
  - `make lint`
  - `make check`
- CI:
  - `Lockfile hygiene` step in `.github/workflows/ci.yml`

## Updating Dependencies

1. Update dependency declarations in the source requirements files.
2. Regenerate both locks with the project-pinned `pip-tools`:
   - `./.venv/bin/pip-compile --generate-hashes --strip-extras -o requirements.lock requirements.txt`
   - `./.venv/bin/pip-compile --allow-unsafe --generate-hashes --strip-extras -o requirements-dev.lock requirements-dev.txt`
3. Run:
   - `./scripts/lockfile_hygiene.sh`
   - `make check`
4. Submit dependency updates in focused PRs.
