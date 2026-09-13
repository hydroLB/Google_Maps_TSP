#!/usr/bin/env bash
set -euo pipefail

log() {
  local level="${1:-INFO}"
  local message="${2:-}"
  printf '[%s] %s\n' "${level}" "${message}" >&2
}

die() {
  local location="${1:-scripts/run.sh.die}"
  local message="${2:-Unknown error}"
  log "ERROR" "${location}: ${message}"
  exit 1
}

repo_root() {
  local location="scripts/run.sh.repo_root"
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)" \
    || die "${location}" "Failed to resolve script directory."
  (cd "${script_dir}/.." >/dev/null 2>&1 && pwd) \
    || die "${location}" "Failed to resolve repository root."
}

_strip_quotes() {
  local raw="${1:-}"
  if [[ "${raw}" =~ ^\".*\"$ ]]; then
    printf '%s' "${raw:1:${#raw}-2}"
    return 0
  fi
  if [[ "${raw}" =~ ^\'.*\'$ ]]; then
    printf '%s' "${raw:1:${#raw}-2}"
    return 0
  fi
  printf '%s' "${raw}"
}

load_dotenv() {
  local location="scripts/run.sh.load_dotenv"
  local root
  root="$(repo_root)"

  local env_path="${root}/.env"
  [[ -f "${env_path}" ]] || return 0

  chmod 600 "${env_path}" \
    || die "${location}" "Failed to restrict .env permissions to the current user."

  # Minimal, safe parser: only accepts allowlisted KEY=VALUE lines and never executes content.
  local line key value
  local line_number=0
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line_number=$((line_number + 1))
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"

    [[ -z "${line}" ]] && continue
    [[ "${line}" == \#* ]] && continue

    if [[ "${line}" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="$(_strip_quotes "${BASH_REMATCH[2]}")"
      case "${key}" in
        GOOGLE_MAPS_API_KEY | FASTEST_ROUTE_ENV | FASTEST_ROUTE_LOG_LEVEL) ;;
        *)
          log "WARN" "Ignoring unsupported .env variable on line ${line_number}; pass process-only overrides in the shell environment."
          continue
          ;;
      esac
      # Environment variables are treated as higher priority than .env. Only fill from .env when
      # the current value is unset or empty.
      if [[ -n "${!key-}" ]]; then
        continue
      fi
      export "${key}=${value}"
    else
      die "${location}" "Invalid .env syntax on line ${line_number}; expected KEY=VALUE."
    fi
  done <"${env_path}"
}

resolve_python() {
  local location="scripts/run.sh.resolve_python"
  local root
  root="$(repo_root)"

  if [[ -n "${FASTEST_ROUTE_PYTHON:-}" ]]; then
    if [[ -x "${FASTEST_ROUTE_PYTHON}" ]]; then
      printf '%s' "${FASTEST_ROUTE_PYTHON}"
      return 0
    fi
    die "${location}" "FASTEST_ROUTE_PYTHON is set but is not executable: ${FASTEST_ROUTE_PYTHON}"
  fi

  if [[ -x "${root}/.venv/bin/python" ]]; then
    printf '%s' "${root}/.venv/bin/python"
    return 0
  fi

  if command -v python3.11 >/dev/null 2>&1; then
    printf '%s' "python3.11"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "python3"
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    printf '%s' "python"
    return 0
  fi

  die "${location}" "No Python interpreter found. Install Python 3.11+ and retry."
}

ensure_python_version() {
  local location="scripts/run.sh.ensure_python_version"
  local py="${1:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing Python interpreter argument."

  "${py}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,11) else 1)' \
    || die "${location}" "Python must be 3.11.x. Detected: $(${py} --version 2>&1 | tr -d '\n')"
}

ensure_venv() {
  local location="scripts/run.sh.ensure_venv"
  local root
  root="$(repo_root)"

  local venv_python="${root}/.venv/bin/python"
  if [[ -x "${venv_python}" ]]; then
    if "${venv_python}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,11) else 1)'; then
      printf '%s' "${venv_python}"
      return 0
    fi
    log "WARN" "Existing .venv is not Python 3.11.x. Recreating the pinned environment."
    rm -rf "${root}/.venv"
  fi

  local base_python
  base_python="$(resolve_python)"
  ensure_python_version "${base_python}"

  log "INFO" "Creating virtual environment at ${root}/.venv"
  "${base_python}" -m venv "${root}/.venv" \
    || die "${location}" "Failed to create virtual environment."

  [[ -x "${venv_python}" ]] || die "${location}" "Virtual environment created but python is missing."
  printf '%s' "${venv_python}"
}

requirements_lockfiles() {
  local location="scripts/run.sh.requirements_lockfiles"
  local root
  root="$(repo_root)"

  local runtime_lock="${root}/requirements.lock"
  [[ -f "${runtime_lock}" ]] || die "${location}" "Missing requirements.lock at ${runtime_lock}"
  printf '%s\n' "${runtime_lock}"
}

ensure_deps_installed() {
  local location="scripts/run.sh.ensure_deps_installed"
  local py="${1:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing venv Python interpreter."

  local root
  root="$(repo_root)"

  local -a lockfiles=()
  local lockfile
  while IFS= read -r lockfile; do
    [[ -n "${lockfile}" ]] && lockfiles+=("${lockfile}")
  done < <(requirements_lockfiles)
  [[ "${#lockfiles[@]}" -gt 0 ]] || die "${location}" "No requirements lockfiles found."

  if ! "${py}" -m pip --version >/dev/null 2>&1; then
    log "WARN" "pip is not usable in the venv. Repairing with ensurepip."
    "${py}" -m ensurepip --upgrade \
      || die "${location}" "Failed to repair pip via ensurepip."
  fi

  local marker_path current_hash stored_hash
  local needs_install="0"
  for lockfile in "${lockfiles[@]}"; do
    marker_path="${root}/.venv/.${lockfile##*/}.sha256"
    current_hash="$("${py}" -c "import hashlib, pathlib, sys; p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest())" "${lockfile}")" \
      || die "${location}" "Failed to compute requirements hash for ${lockfile}."
    stored_hash=""
    if [[ -f "${marker_path}" ]]; then
      stored_hash="$(cat "${marker_path}" 2>/dev/null || true)"
    fi
    if [[ "${current_hash}" != "${stored_hash}" ]]; then
      needs_install="1"
      break
    fi
  done

  if [[ "${needs_install}" == "0" ]]; then
    return 0
  fi

  log "INFO" "Installing dependencies from the runtime lockfile"
  for lockfile in "${lockfiles[@]}"; do
    marker_path="${root}/.venv/.${lockfile##*/}.sha256"
    current_hash="$("${py}" -c "import hashlib, pathlib, sys; p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest())" "${lockfile}")" \
      || die "${location}" "Failed to compute requirements hash for ${lockfile}."
    stored_hash=""
    if [[ -f "${marker_path}" ]]; then
      stored_hash="$(cat "${marker_path}" 2>/dev/null || true)"
    fi

    if [[ "${current_hash}" == "${stored_hash}" ]]; then
      continue
    fi

    log "INFO" "Installing dependencies from ${lockfile##*/}"
    "${py}" -m pip install --require-hashes -r "${lockfile}" \
      || die "${location}" "Dependency installation failed. lockfile=${lockfile}"
    printf '%s' "${current_hash}" >"${marker_path}" \
      || die "${location}" "Failed to write dependency marker file: ${marker_path}"
  done
}

requires_gui() {
  local arg
  for arg in "$@"; do
    case "${arg}" in
      -h | --help | --check-config) return 1 ;;
    esac
  done
  return 0
}

preflight_api_key() {
  local location="scripts/run.sh.preflight_api_key"
  requires_gui "$@" || return 0
  local arg
  for arg in "$@"; do
    [[ "${arg}" == "--demo" ]] && return 0
  done
  local env_name="${FASTEST_ROUTE_ENV:-dev}"
  if [[ "${env_name}" == "test" || "${env_name}" == "ci" ]]; then
    return 0
  fi
  if [[ -z "${GOOGLE_MAPS_API_KEY:-}" ]]; then
    log "WARN" "GOOGLE_MAPS_API_KEY is not set. The GUI will prompt you to enter it."
  fi
}

preflight_tkinter() {
  local location="scripts/run.sh.preflight_tkinter"
  local py="${1:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing Python interpreter argument."
  shift
  requires_gui "$@" || return 0

  local env_name="${FASTEST_ROUTE_ENV:-dev}"
  if [[ "${env_name}" == "test" || "${env_name}" == "ci" ]]; then
    return 0
  fi

  if [[ "${FASTEST_ROUTE_SKIP_TK_PREFLIGHT:-}" == "1" ]]; then
    return 0
  fi

  local check_code
  check_code="$(
    cat <<'PY'
import sys

try:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    root.destroy()
except Exception as exc:
    print(
        f"Tkinter preflight failed: {exc.__class__.__name__}: {exc}",
        file=sys.stderr,
    )
    raise
PY
  )"

  # Execute via a pipeline so stdout/stderr stay in the terminal while suppressing bash "Abort trap" noise.
  # We temporarily disable `pipefail` and inspect `PIPESTATUS[0]` so failures are still detected.
  set +o pipefail
  "${py}" -c "${check_code}" 2>&1 | cat >&2
  local python_status="${PIPESTATUS[0]}"
  set -o pipefail

  if [[ "${python_status}" -ne 0 ]]; then
    die "${location}" $'Tkinter failed to initialize a GUI window.\n\nCommon fixes:\n- Run from a local desktop session (not SSH).\n- Use a Python build with working Tk support (python.org installer is the safest on macOS).\n- If using pyenv, install Tcl/Tk and rebuild Python.\n\nYou can also point the launcher at a known-good interpreter with FASTEST_ROUTE_PYTHON=/path/to/python.'
  fi
}

is_live_reload_enabled() {
  local raw="${FASTEST_ROUTE_LIVE_RELOAD:-0}"
  case "${raw}" in
    1 | [Tt][Rr][Uu][Ee] | [Yy][Ee][Ss] | [Oo][Nn]) return 0 ;;
    *) return 1 ;;
  esac
}

run_gui_entrypoint() {
  local location="scripts/run.sh.run_gui_entrypoint"
  local py="${1:-}"
  local root="${2:-}"
  [[ -n "${py}" ]] || die "${location}" "Missing Python interpreter argument."
  [[ -n "${root}" ]] || die "${location}" "Missing repository root argument."
  shift 2
  local -a app_args=("$@")

  local app_entrypoint="${root}/TSP_GOOGLE_MAPS/main.py"
  [[ -f "${app_entrypoint}" ]] || die "${location}" "Missing app entrypoint: ${app_entrypoint}"

  if ! is_live_reload_enabled; then
    "${py}" "${app_entrypoint}" "${app_args[@]}"
    return $?
  fi

  local watch_script="${root}/scripts/dev_watch.py"
  [[ -f "${watch_script}" ]] || die "${location}" "Missing live-reload watcher script: ${watch_script}"

  local poll_interval="${FASTEST_ROUTE_WATCH_POLL_SECONDS:-0.75}"
  local shutdown_timeout="${FASTEST_ROUTE_WATCH_SHUTDOWN_TIMEOUT_SECONDS:-4.0}"
  log "INFO" "Starting GUI with live reload enabled. Save GUI files to trigger restarts."
  "${py}" "${watch_script}" \
    --poll-interval-seconds "${poll_interval}" \
    --graceful-timeout-seconds "${shutdown_timeout}" \
    --watch-root "${root}/TSP_GOOGLE_MAPS/main.py" \
    --watch-root "${root}/TSP_GOOGLE_MAPS/fastest_route/presentation" \
    --watch-root "${root}/TSP_GOOGLE_MAPS/config.toml" \
    --watch-extension ".py" \
    --watch-extension ".toml" \
    --watch-extension ".env" \
    -- "${py}" "${app_entrypoint}" "${app_args[@]}"
}

main() {
  local root
  root="$(repo_root)"

  cd "${root}" || die "scripts/run.sh.main" "Failed to cd to repository root."
  load_dotenv
  preflight_api_key "$@"

  local py
  py="$(ensure_venv)"
  ensure_deps_installed "${py}"
  preflight_tkinter "${py}" "$@"

  local py_version
  py_version="$("${py}" --version 2>&1 | tr -d '\n' || true)"
  if [[ -n "${py_version}" ]]; then
    log "INFO" "Using Python: ${py} (${py_version})"
  else
    log "INFO" "Using Python: ${py}"
  fi

  if ! requires_gui "$@"; then
    log "INFO" "Running command-line validation."
  elif is_live_reload_enabled; then
    log "INFO" "Starting GUI in live-reload mode."
  else
    log "INFO" "Starting GUI. If no window appears, check that it is not behind other windows."
  fi
  if ! run_gui_entrypoint "${py}" "${root}" "$@"; then
    die "scripts/run.sh.main" $'The GUI process exited with a non-zero status.\n\nIf you saw no output, re-run with FASTEST_ROUTE_LOG_LEVEL=DEBUG to increase verbosity, or set FASTEST_ROUTE_PYTHON to a known-good interpreter.'
  fi
}

main "$@"
