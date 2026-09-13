# Security Policy

## Supported Version

Security updates are applied to the current `main` branch.

## Reporting a Vulnerability

Do not open public issues for suspected vulnerabilities.

Preferred process:

1. Open a private GitHub security advisory for this repository.
2. Include:
   - Impacted file/module and version/commit.
   - Reproduction steps and required config.
   - Impact assessment (confidentiality, integrity, availability).
   - Suggested fix or mitigation, if available.
3. Wait for maintainer acknowledgement before public disclosure.

Expected response targets:

- Initial acknowledgement: within 3 business days.
- Triage classification: within 7 business days.
- Fix timeline: communicated after triage based on severity.

## Disclosure Policy

- Coordinate disclosure with maintainers.
- Avoid publishing exploit details before a fix is released.
- Credit reporters in release notes when requested.

## Local Security Checks

Run before opening a PR:

```bash
make lint
make check
```

Local secret scanning guidance:

1. Install [gitleaks](https://github.com/gitleaks/gitleaks).
2. Scan the repository root:

```bash
gitleaks detect --source . --config gitleaks.toml --redact
```

3. If a secret is found:
   - Revoke/rotate the credential immediately.
   - Remove the secret from tracked files.
   - Re-run scan until clean.

Lockfile consistency guidance:

- Lockfile policy is defined in `docs/security/lockfile-hygiene.md`.
- Run `./scripts/lockfile_hygiene.sh` before merging dependency changes.
- Automated dependency update PRs are intentionally not enabled for this repository.
  Dependency changes should be reviewed in focused PRs with `pip-audit`,
  lockfile hygiene, and the full quality gate passing.

## Threat Model Notes

Threat model notes for key entry surfaces are documented in:

- `docs/security/threat-model.md`
