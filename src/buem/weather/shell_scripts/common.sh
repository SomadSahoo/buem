#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 Weather Pipeline — Shared Shell Configuration
# ──────────────────────────────────────────────────────────────────────────────
# Sourced by all pipeline shell scripts.  Centralises:
#   - Conda environment activation (direct PATH manipulation)
#   - .env file loading
#   - PYTHONPATH setup for standalone deployment
#   - Core/thread detection from SLURM or fallback
#   - Common directory variables
#
# SLURM copies submitted scripts to /var/spool/ before execution, so
# $0 / BASH_SOURCE are unreliable for path resolution.  All paths are
# derived from environment variables with sensible $HOME-based defaults.
#
# Usage (from another script):
#   source "$(dirname "$0")/common.sh"    # interactive only
#   # OR (SLURM safe):
#   source "${COSMO_SCRIPTS_DIR:-${HOME}/buem/src/buem/weather/shell_scripts}/common.sh"
# ──────────────────────────────────────────────────────────────────────────────

# Guard against double-sourcing
if [ "${_COSMO_COMMON_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || true
fi
_COSMO_COMMON_LOADED=1

# ── Repository / source layout ────────────────────────────────────────────
export COSMO_REPO_DIR="${COSMO_REPO_DIR:-${HOME}/buem}"
export COSMO_SRC_DIR="${COSMO_SRC_DIR:-${COSMO_REPO_DIR}/src}"
export COSMO_SCRIPTS_DIR="${COSMO_SCRIPTS_DIR:-${COSMO_SRC_DIR}/buem/weather/shell_scripts}"

# ── Load .env if present ──────────────────────────────────────────────────
for _candidate in "${COSMO_REPO_DIR}/.env" \
                  "${COSMO_SRC_DIR}/buem/weather/.env" \
                  "${HOME}/.env"; do
    if [ -f "$_candidate" ]; then
        echo "[common] Loading .env from $_candidate"
        set -a
        source "$_candidate"
        set +a
        break
    fi
done
unset _candidate

# ── Core / thread detection ───────────────────────────────────────────────
# Priority: SLURM > .env > nproc > 16
export COSMO_NCORES="${SLURM_CPUS_PER_TASK:-${COSMO_NCORES:-$(nproc 2>/dev/null || echo 16)}}"
export COSMO_THREADS_PER_JOB="${COSMO_THREADS_PER_JOB:-4}"

# ── Common directories ───────────────────────────────────────────────────
export COSMO_WORK_DIR="${COSMO_WORK_DIR:-${HOME}/buem_weather}"
export COSMO_DOWNLOAD_DIR="${COSMO_WORK_DIR}/download"
export COSMO_DECOMPRESS_DIR="${COSMO_WORK_DIR}/decompress"
export COSMO_OUTPUT_DIR="${COSMO_WORK_DIR}/output"

# ── Default pipeline parameters ──────────────────────────────────────────
export COSMO_YEAR="${COSMO_YEAR:-2018}"
export COSMO_MONTHS="${COSMO_MONTHS:-01,02,03,04,05,06,07,08,09,10,11,12}"
export COSMO_BASE_URL="${COSMO_BASE_URL:-https://opendata.dwd.de/climate_environment/REA/COSMO_REA6/hourly/2D}"

# Attributes array (not exported — sourced into the calling script)
COSMO_ATTRS=("SWDIFDS_RAD" "SWDIRS_RAD" "T_2M" "U_10M" "V_10M")

# ── HDF5 / NetCDF safety ─────────────────────────────────────────────────
export HDF5_USE_FILE_LOCKING="${HDF5_USE_FILE_LOCKING:-FALSE}"

# ── Conda environment activation ─────────────────────────────────────────
# Activates by prepending env bin/ to PATH — no conda binary required.
_activate_conda_env() {
    local env_name="${COSMO_CONDA_ENV:-weather_env}"
    local env_dir="${COSMO_CONDA_ENV_DIR:-${HOME}/.conda/envs/${env_name}}"

    if [ ! -d "${env_dir}/bin" ]; then
        echo "[common] ERROR: Conda environment not found: ${env_dir}/bin"
        echo "  Create it on the login node:  bash setup_env.sh"
        return 1
    fi

    export PATH="${env_dir}/bin:${PATH}"
    export CONDA_DEFAULT_ENV="${env_name}"
    export CONDA_PREFIX="${env_dir}"
    echo "[common] Activated conda env: ${env_dir}"
    echo "[common] Python: $(which python) ($(python --version 2>&1))"
}

# ── PYTHONPATH setup for standalone deployment ────────────────────────────
_setup_pythonpath() {
    export PYTHONPATH="${COSMO_SRC_DIR}:${PYTHONPATH:-}"

    # Create buem/__init__.py if only the weather sub-package was uploaded
    local init_file="${COSMO_SRC_DIR}/buem/__init__.py"
    if [ ! -f "${init_file}" ]; then
        echo "[common] Creating minimal buem/__init__.py for standalone deployment"
        mkdir -p "${COSMO_SRC_DIR}/buem"
        touch "${init_file}"
    fi
}

# ── Decompressor detection ────────────────────────────────────────────────
_detect_decompressor() {
    if [ -n "${COSMO_DECOMPRESSOR:-}" ] && command -v "${COSMO_DECOMPRESSOR}" >/dev/null 2>&1; then
        echo "${COSMO_DECOMPRESSOR}"
    elif command -v lbzip2 >/dev/null 2>&1; then
        echo "lbzip2"
    elif command -v pbzip2 >/dev/null 2>&1; then
        echo "pbzip2"
    else
        echo "bzip2"
    fi
}

# ── Logging helper ────────────────────────────────────────────────────────
_log_header() {
    local title="$1"
    echo "============================================================"
    echo "${title}"
    echo "  Job ID:     ${SLURM_JOB_ID:-local}"
    echo "  Node:       $(hostname)"
    echo "  CPUs:       ${COSMO_NCORES}"
    echo "  Year:       ${COSMO_YEAR}"
    echo "  Months:     ${COSMO_MONTHS}"
    echo "  Work dir:   ${COSMO_WORK_DIR}"
    echo "  Started:    $(date)"
    echo "============================================================"
}
