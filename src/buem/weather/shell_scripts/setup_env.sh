#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 Weather Pipeline — Conda Environment Setup
# ──────────────────────────────────────────────────────────────────────────────
# Creates (or updates) the conda environment required for the weather
# processing pipeline on a Linux HPC server (e.g. Snellius).
#
# Only weather-specific packages are installed.  The full buem package
# (cvxpy, flask, etc.) is NOT needed on the server.
#
# Usage:
#   bash setup_env.sh                   # create/update the weather_env environment
#   bash setup_env.sh my_custom_env     # use a custom environment name
#
# Prerequisites:
#   - An Lmod module system with Miniconda, OR conda already in PATH.
#   - Internet access to conda-forge channel.
#
# On Snellius (SURF) the system Miniconda requires `module load` before
# conda commands work.  Set COSMO_CONDA_TOOLCHAIN and COSMO_CONDA_MODULE
# in .env to match your system, or leave them empty if conda is already
# in your PATH.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ENV_NAME="${1:-weather_env}"

echo "============================================================"
echo "COSMO-REA6 Weather Pipeline — Conda Environment Setup"
echo "  Environment: ${ENV_NAME}"
echo "  Date:        $(date)"
echo "============================================================"

# Check conda is available; if not, try module load
if ! command -v conda &>/dev/null; then
    # Try loading conda via Lmod (common on HPC systems like Snellius)
    TOOLCHAIN="${COSMO_CONDA_TOOLCHAIN:-2025}"
    MODULE="${COSMO_CONDA_MODULE:-Miniconda3/25.5.1-1}"
    echo "conda not in PATH — trying: module load ${TOOLCHAIN} && module load ${MODULE}"
    if command -v module &>/dev/null; then
        module load "${TOOLCHAIN}" 2>/dev/null || true
        module load "${MODULE}" 2>/dev/null || true
    fi
    if ! command -v conda &>/dev/null; then
        echo "ERROR: conda still not found after module load."
        echo "  Set COSMO_CONDA_TOOLCHAIN and COSMO_CONDA_MODULE in .env,"
        echo "  or install Miniconda in your home directory."
        exit 1
    fi
fi
echo "Using conda: $(conda --version)"

# Initialize conda shell hook (required before 'conda activate')
eval "$(conda shell.bash hook)"

# Prefer the weather_env.yml file if available (same directory as this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_YML="${SCRIPT_DIR}/../weather_env.yml"

if [ -f "${ENV_YML}" ]; then
    echo "Found weather_env.yml — creating environment from file..."
    if conda env list | grep -qw "${ENV_NAME}"; then
        echo "Environment '${ENV_NAME}' already exists — updating."
        conda env update -n "${ENV_NAME}" -f "${ENV_YML}" --prune
    else
        conda env create -n "${ENV_NAME}" -f "${ENV_YML}"
    fi
else
    echo "weather_env.yml not found — installing packages manually..."

    # Create the environment if it doesn't exist
    if conda env list | grep -qw "${ENV_NAME}"; then
        echo "Environment '${ENV_NAME}' already exists — updating."
    else
        echo "Creating new environment '${ENV_NAME}' with Python 3.13..."
        conda create -y -n "${ENV_NAME}" python=3.13 -c conda-forge
    fi

    echo ""
    echo "Installing weather pipeline packages from conda-forge..."
    conda install -y -n "${ENV_NAME}" -c conda-forge \
        cfgrib \
        dask \
        eccodes \
        netcdf4 \
        numpy \
        pandas \
        pvlib \
        pyarrow \
        pyproj \
        python-dotenv \
        scipy \
        xarray
fi

echo ""
echo "============================================================"
echo "Environment '${ENV_NAME}' is ready."
echo ""
echo "Activate with:"
echo "  conda activate ${ENV_NAME}"
echo ""
echo "Then run the pipeline:"
echo "  python -m buem.weather info"
echo "  python -m buem.weather run --months 1"
echo "============================================================"
