# Required Checks for `main`

Protect `main` by requiring:

- `ci / quality`

Also require `code-scanning / codeql` only after GitHub code scanning is enabled for the
repository and the workflow has completed successfully. A configured workflow is not evidence that
the repository plan/settings currently accept SARIF uploads; do not create a permanently impossible
branch rule.

The `quality` job must stay green and includes these gates:

1. Format check (`ruff format --check`)
2. Lint (`ruff check`)
3. Type check (`mypy`)
4. Lockfile hygiene guard (`scripts/lockfile_hygiene.sh`)
5. Repository hygiene guard (`scripts/repo_hygiene.sh`, including full layer dependency direction enforcement and duplicate copy artifact checks)
6. Test suite (`pytest` with non-presentation branch coverage + critical-module coverage threshold)
7. Build (`python -m build --no-isolation` from the hash-locked development environment)
8. Benchmark smoke (`scripts/bench.sh`, with JSON measurements uploaded for review)
9. Security scan (`bandit`)
10. Strict dependency audit (`pip-audit` without dependency re-resolution)
11. Secret scan (`gitleaks`)
12. Working tree guard (fails when tracked files are modified by CI commands)

The workflow must run on every branch push and every pull request so hygiene, security, and dependency-lock reproducibility regressions are caught before code reaches `main`. Release archives are not currently asserted to be byte-for-byte reproducible.

When enabled, `code-scanning / codeql` runs Python CodeQL and uploads results to GitHub code
scanning. Bandit remains part of `ci / quality` regardless of CodeQL availability.

If any required check fails, merging into `main` must be blocked.
