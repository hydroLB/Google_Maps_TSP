#!/usr/bin/env bash
set -euo pipefail

die() {
  local location="${1:-scripts/repo_hygiene.sh.die}"
  local message="${2:-Unknown error}"
  printf '[ERROR] %s: %s\n' "${location}" "${message}" >&2
  exit 1
}

repo_root() {
  local location="scripts/repo_hygiene.sh.repo_root"
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)" \
    || die "${location}" "Failed to resolve script directory."
  (cd "${script_dir}/.." >/dev/null 2>&1 && pwd) \
    || die "${location}" "Failed to resolve repository root."
}

check_tracked_generated_artifacts() {
  local location="scripts/repo_hygiene.sh.check_tracked_generated_artifacts"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local tracked
  tracked="$(
    git -C "${root}" ls-files | \
      grep -E '(^|/)\.DS_Store$|(^|/)\.coverage(\..*)?$|(^|/)\.benchmarks/|(^|/)\.codex/|(^|/)__pycache__/|\.egg-info/|(^|/)artifacts/|(^|/)build/|(^|/)dist/' || true
  )"
  if [[ -n "${tracked}" ]]; then
    {
      echo "Tracked generated artifacts are not allowed:"
      echo "${tracked}"
      echo "Remove these paths from git tracking before merging."
    } >&2
    die "${location}" "Repository contains tracked generated artifacts."
  fi
}

check_tracked_secret_material() {
  local location="scripts/repo_hygiene.sh.check_tracked_secret_material"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local flagged=""
  local file_path=""
  while IFS= read -r file_path; do
    case "${file_path}" in
      .env|.env.*|*.pem|*.key|*.crt|*.cer|*.der|*.p12|*.pfx|*.jks|*.keystore|*.kubeconfig|id_rsa|id_rsa.pub|id_ed25519|id_ed25519.pub|secrets/*|credentials/*)
        case "${file_path}" in
          .env.example|.env.*.example)
            ;;
          *)
            flagged+="${file_path}"$'\n'
            ;;
        esac
        ;;
    esac
  done < <(git -C "${root}" ls-files)

  if [[ -n "${flagged}" ]]; then
    {
      echo "Tracked secret-bearing files are not allowed:"
      printf '%s' "${flagged}"
      echo "Keep secrets in local-only files such as .env and commit only sanitized examples."
    } >&2
    die "${location}" "Repository contains tracked secret-bearing files."
  fi
}

check_required_repo_files() {
  local location="scripts/repo_hygiene.sh.check_required_repo_files"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local required_files=(
    ".editorconfig"
    ".env.example"
    ".githooks/pre-commit"
    ".githooks/pre-push"
    ".gitattributes"
    ".github/workflows/ci.yml"
    ".gitignore"
    ".pre-commit-config.yaml"
    ".python-version"
    "Makefile"
    "README.md"
    "SECURITY.md"
    "gitleaks.toml"
    "pyproject.toml"
    "requirements.lock"
    "requirements-dev.lock"
    "scripts/bootstrap_venv.sh"
    "scripts/check.sh"
    "scripts/repo_hygiene.sh"
    "TSP_GOOGLE_MAPS/config.toml"
    "TSP_GOOGLE_MAPS/fastest_route/config/default.toml"
  )

  local missing=""
  local required_file=""
  for required_file in "${required_files[@]}"; do
    if ! git -C "${root}" ls-files --error-unmatch "${required_file}" >/dev/null 2>&1; then
      missing+="${required_file}"$'\n'
    fi
  done

  if [[ -n "${missing}" ]]; then
    {
      echo "Required tracked repository files are missing:"
      printf '%s' "${missing}"
      echo "Restore these files so a fresh clone can bootstrap, validate, and run deterministically."
    } >&2
    die "${location}" "Repository is missing recovery-critical tracked files."
  fi
}

check_packaged_config_sync() {
  # The source launcher and installed wheel resolve different physical files. Keeping them
  # byte-identical prevents a build from shipping defaults that were never exercised locally.
  local location="scripts/repo_hygiene.sh.check_packaged_config_sync"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local source_config="${root}/TSP_GOOGLE_MAPS/config.toml"
  local packaged_config="${root}/TSP_GOOGLE_MAPS/fastest_route/config/default.toml"
  if ! cmp -s "${source_config}" "${packaged_config}"; then
    die "${location}" "Source and packaged default configuration files have drifted."
  fi
}

check_disallowed_repo_files() {
  local location="scripts/repo_hygiene.sh.check_disallowed_repo_files"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local disallowed=""
  local file_path=""
  while IFS= read -r file_path; do
    case "${file_path}" in
      .github/dependabot.yml|pre-commit|pre-commit\ 2|pre-push|pre-push\ 2|post-commit|git-autosnap.sh|gitleaks-prepush.json)
        disallowed+="${file_path}"$'\n'
        ;;
    esac
  done < <(git -C "${root}" ls-files)

  if [[ -n "${disallowed}" ]]; then
    {
      echo "Tracked files are not allowed because they re-enable banned automation or legacy hooks:"
      printf '%s' "${disallowed}"
      echo "Use repository-managed hooks under .githooks/ and keep Dependabot disabled."
    } >&2
    die "${location}" "Repository contains disallowed tracked automation files."
  fi
}

check_tracked_duplicate_copy_artifacts() {
  local location="scripts/repo_hygiene.sh.check_tracked_duplicate_copy_artifacts"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local flagged=""
  local file_path=""
  while IFS= read -r -d '' file_path; do
    local file_name
    file_name="$(basename "${file_path}")"
    local base_name=""

    if [[ "${file_name}" == *" 2."* ]]; then
      base_name="${file_name/ 2./.}"
    elif [[ "${file_name}" == *" 2" ]]; then
      base_name="${file_name% 2}"
    else
      continue
    fi

    local dir_name
    dir_name="$(dirname "${file_path}")"
    local canonical="${base_name}"
    if [[ "${dir_name}" != "." ]]; then
      canonical="${dir_name}/${base_name}"
    fi

    if git -C "${root}" ls-files --error-unmatch "${canonical}" >/dev/null 2>&1; then
      flagged+="${file_path} (canonical: ${canonical})"$'\n'
    fi
  done < <(git -C "${root}" ls-files -z)

  if [[ -n "${flagged}" ]]; then
    {
      echo "Tracked duplicate copy artifacts are not allowed:"
      printf '%s' "${flagged}"
      echo "Keep the canonical file only, or rename intentionally so it is not a copy artifact."
    } >&2
    die "${location}" "Repository contains tracked duplicate copy artifacts."
  fi
}

check_untracked_non_ignored_files() {
  local location="scripts/repo_hygiene.sh.check_untracked_non_ignored_files"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local untracked
  untracked="$(git -C "${root}" ls-files --others --exclude-standard)"
  if [[ -n "${untracked}" ]]; then
    {
      echo "Untracked files must be added to git or ignored explicitly:"
      echo "${untracked}"
      echo "Update .gitignore for local-only files or git add files that belong in the repository."
    } >&2
    die "${location}" "Repository contains untracked non-ignored files."
  fi
}

check_python_filenames() {
  local location="scripts/repo_hygiene.sh.check_python_filenames"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local invalid
  invalid="$(
    git -C "${root}" ls-files '*.py' | \
      while IFS= read -r file_path; do
        file_name="$(basename "${file_path}")"
        if [[ "${file_name}" == "__init__.py" || "${file_name}" == "__main__.py" ]]; then
          continue
        fi
        if [[ ! "${file_name}" =~ ^[a-z][a-z0-9_]*\.py$ ]]; then
          printf '%s\n' "${file_path}"
        fi
      done
  )"
  if [[ -n "${invalid}" ]]; then
    {
      echo "Python files must use snake_case module names:"
      echo "${invalid}"
      echo "Rename files to match ^[a-z][a-z0-9_]*\\.py$ (or a standard __init__.py/__main__.py module)."
    } >&2
    die "${location}" "Repository contains non-standard python file names."
  fi
}

resolve_python_for_checks() {
  local location="scripts/repo_hygiene.sh.resolve_python_for_checks"
  local root
  root="$(repo_root)"

  if [[ -n "${FASTEST_ROUTE_PYTHON:-}" ]]; then
    [[ -x "${FASTEST_ROUTE_PYTHON}" ]] \
      || die "${location}" "FASTEST_ROUTE_PYTHON is not executable: ${FASTEST_ROUTE_PYTHON}"
    printf '%s\n' "${FASTEST_ROUTE_PYTHON}"
    return 0
  fi

  if [[ -x "${root}/.venv/bin/python" ]]; then
    printf '%s\n' "${root}/.venv/bin/python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    printf '%s\n' "python"
    return 0
  fi
  die "${location}" "Python interpreter is required for dependency direction checks."
}

check_layer_dependency_rules() {
  local location="scripts/repo_hygiene.sh.check_layer_dependency_rules"
  local root="${1:-}"
  [[ -n "${root}" ]] || die "${location}" "Missing repository root."

  local package_root="${root}/TSP_GOOGLE_MAPS/fastest_route"
  [[ -d "${package_root}" ]] || die "${location}" "Missing package directory: ${package_root}"

  local py
  py="$(resolve_python_for_checks)"

  local output
  set +e
  output="$(
    "${py}" - "${package_root}" <<'PY'
import ast
import pathlib
import sys

package_root = pathlib.Path(sys.argv[1]).resolve()
layers = {"config", "core", "infrastructure", "observability", "presentation", "shared"}

allowed = {
    "config": {"config", "shared"},
    "core": {"core", "config", "observability", "shared"},
    "infrastructure": {"config", "infrastructure", "observability", "shared"},
    "observability": {"observability", "shared"},
    "presentation": {"config", "core", "infrastructure", "observability", "presentation", "shared"},
    "shared": {"shared"},
}


def module_from_path(file_path: pathlib.Path) -> list[str]:
    rel = file_path.relative_to(package_root)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ["fastest_route", *parts]


def resolve_import_module(file_path: pathlib.Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    current = module_from_path(file_path)
    if not current:
        return None
    drop = max(1, node.level)
    if len(current) < drop:
        return None
    base = current[:-drop]
    if node.module:
        base.extend(node.module.split("."))
    if not base:
        return None
    return ".".join(base)


def layer_from_module(module_name: str) -> str | None:
    if not module_name.startswith("fastest_route."):
        return None
    parts = module_name.split(".")
    if len(parts) < 2:
        return None
    layer = parts[1]
    if layer not in layers:
        return None
    return layer


violations: list[tuple[str, int, str, str, str, str]] = []

for file_path in sorted(package_root.rglob("*.py")):
    source_layer = layer_from_module(".".join(module_from_path(file_path)))
    if source_layer is None:
        continue
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target_module = alias.name
                target_layer = layer_from_module(target_module)
                if target_layer is None:
                    continue
                if target_layer not in allowed[source_layer]:
                    violations.append(
                        (
                            str(file_path),
                            node.lineno,
                            source_layer,
                            target_layer,
                            target_module,
                            f"import {target_module}",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            target_module = resolve_import_module(file_path, node)
            if not target_module:
                continue
            target_layer = layer_from_module(target_module)
            if target_layer is None:
                continue
            if target_layer not in allowed[source_layer]:
                raw = f"from {'.' * node.level + (node.module or '')} import ..."
                violations.append(
                    (
                        str(file_path),
                        node.lineno,
                        source_layer,
                        target_layer,
                        target_module,
                        raw,
                    )
                )

if violations:
    print("Layer dependency violations detected:")
    for file_path, lineno, source_layer, target_layer, target_module, raw in violations:
        allowed_targets = ", ".join(sorted(allowed[source_layer]))
        print(
            f"- {source_layer} -> {target_layer} is not allowed "
            f"(allowed: {allowed_targets}) | {file_path}:{lineno} | {raw} | resolved={target_module}"
        )
    sys.exit(1)
PY
  )"
  local rc=$?
  set -e

  if [[ ${rc} -ne 0 ]]; then
    [[ -n "${output}" ]] && printf '%s\n' "${output}" >&2
    die "${location}" "Found forbidden cross-layer imports."
  fi
}

main() {
  local root
  root="$(repo_root)"
  check_tracked_generated_artifacts "${root}"
  check_tracked_secret_material "${root}"
  check_required_repo_files "${root}"
  check_packaged_config_sync "${root}"
  check_disallowed_repo_files "${root}"
  check_tracked_duplicate_copy_artifacts "${root}"
  check_untracked_non_ignored_files "${root}"
  check_python_filenames "${root}"
  check_layer_dependency_rules "${root}"
}

main "$@"
