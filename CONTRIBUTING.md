# Contributing

## Scope

This repository is maintained with strict quality and dependency-lock reproducibility standards. Every contribution must preserve existing behavior unless a behavior change is explicitly intended and tested; release archives are not currently claimed to be byte-for-byte reproducible.

## Prerequisites

- Python 3.11.x (pinned in `.python-version`)
- Git
- Bash and GNU Make for the documented macOS/Linux workflow; Windows contributors should use WSL
  or translate the wrapper commands to their Python equivalents
- Local desktop session with Tk support if you plan to run the GUI

## First-time setup

1. Clone the repository.
2. Run `make setup`.
3. Verify hooks are installed: `./.venv/bin/pre-commit --version`.
4. Copy the environment template to the source checkout's stable credential path:
   `cp .env.example .env` from the repository root.
5. Optionally set `GOOGLE_MAPS_API_KEY` in `.env` for live API calls.

Reference onboarding validation:

- `docs/onboarding/new-contributor-dry-run.md`

## Development workflow

1. Create a focused branch.
2. Make changes with tests.
3. Run fast local hooks as needed: `./.venv/bin/pre-commit run --all-files`.
4. Run `make check` before pushing.
5. Open a pull request using the repository PR template.

## Quality gates

Local quality gates are deterministic and run through the pinned toolchain:

- `make lint`
- `make test`
- `make build`
- `make check`
- `./.venv/bin/pre-commit run --all-files` (fast local gate)

`make check` is the source-of-truth required pre-push command. The installed `pre-push` hook runs it automatically, and `pre-commit` remains the faster local safety net while iterating.

## Testing expectations

- Add or update tests for all behavior changes.
- Keep tests deterministic.
- Prefer unit tests for pure logic and integration tests for I/O boundaries.
- Preserve or improve coverage on touched critical modules. The configured aggregate percentage
  excludes `fastest_route.presentation`; add targeted presentation tests for GUI workflow changes.
- Treat `tests/e2e` as a service-level workflow smoke, not a real-window GUI test. Manually exercise
  affected Tk flows on a Tk-enabled desktop and describe that check in the PR.

## Commit and PR expectations

- Keep diffs small and focused.
- Write clear commit messages describing intent.
- Include rationale for non-obvious design choices in PR description.
- Do not merge if CI is failing.

## Security and secrets

- Never commit real secrets, tokens, or API keys.
- Keep `.env` local only. It stores the API key as plaintext and depends on workstation filesystem
  protections; never attach it to an issue or PR.
- Validate logging changes do not expose sensitive values.
- Follow `SECURITY.md` for vulnerability reporting and local secret scanning.
- Run `./scripts/lockfile_hygiene.sh` when dependency files change.

## Reporting issues

Use the issue templates for bugs and feature proposals so reports include reproducible context.
