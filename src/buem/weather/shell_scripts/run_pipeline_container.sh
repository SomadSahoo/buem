#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 Weather Pipeline — Containerised SLURM Job (Snellius)
# ──────────────────────────────────────────────────────────────────────────────
# Runs the weather pipeline inside an Apptainer container on Snellius.
#
# The image contains only conda deps + system tools (deps-only).
# Source code and data are bind-mounted from the host:
#   ~/buem/src        →  /app/src   (Python source code)
#   ~/buem_weather    →  /data      (download, decompress, output directories)
#
# Usage:
#   sbatch run_pipeline_container.sh                    # full year
#   sbatch run_pipeline_container.sh --months 1         # single-month test
#   sbatch run_pipeline_container.sh --skip-download --months 1 2 3
#
# After code changes — just scp and re-run (no image rebuild needed):
#   scp -r src/buem/weather ssahoo@snellius.surf.nl:~/buem/src/buem/
#   sbatch src/buem/weather/shell_scripts/run_pipeline_container.sh --months 1
#
# Rebuild the SIF only when weather_env.yml changes:
#   cd ~/buem && bash src/buem/weather/shell_scripts/build_container.sh def
#
# Environment variables:
#   COSMO_SIF_PATH   — Path to the .sif image  (default: ~/buem/buem_weather.sif)
#   COSMO_WORK_DIR   — Host data directory      (default: ~/buem_weather)
#   COSMO_SRC_DIR    — Host source directory     (default: ~/buem/src)
# ──────────────────────────────────────────────────────────────────────────────

#SBATCH -J cosmo_container
#SBATCH -t 00:45:00
#SBATCH -p rome
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -o slurm_container.%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────
SIF_PATH="${COSMO_SIF_PATH:-${HOME}/buem/buem_weather.sif}"
WORK_DIR="${COSMO_WORK_DIR:-${HOME}/buem_weather}"
SRC_DIR="${COSMO_SRC_DIR:-${HOME}/buem/src}"

# ── Validate ──────────────────────────────────────────────────────────────
if [ ! -f "${SIF_PATH}" ]; then
    echo "ERROR: SIF image not found: ${SIF_PATH}"
    echo "  Build with:  cd ~/buem && bash src/buem/weather/shell_scripts/build_container.sh def"
    exit 1
fi

if [ ! -d "${SRC_DIR}/buem/weather" ]; then
    echo "ERROR: Source code not found: ${SRC_DIR}/buem/weather"
    echo "  Upload with:  scp -r src/buem/weather ssahoo@snellius.surf.nl:~/buem/src/buem/"
    exit 1
fi

# Create host directories if they don't exist
mkdir -p "${WORK_DIR}"

# ── Print job info ────────────────────────────────────────────────────────
echo "============================================================"
echo "COSMO-REA6 Weather Pipeline — Containerised SLURM Job"
echo "============================================================"
echo "  SIF image:    ${SIF_PATH}"
echo "  Source dir:   ${SRC_DIR}"
echo "  Data dir:     ${WORK_DIR}"
echo "  SLURM job:    ${SLURM_JOB_ID:-local}"
echo "  CPUs:         ${SLURM_CPUS_PER_TASK:-$(nproc 2>/dev/null || echo 16)}"
echo "  Node:         $(hostname)"
echo "  Started:      $(date)"
echo "============================================================"
echo ""

# ── Suppress XALT LD_PRELOAD warnings inside the container ────────────────
# See: SURF FAQ "When I use Singularity, I get an LD_PRELOAD error"
unset LD_PRELOAD 2>/dev/null || true

# ── Run the pipeline in the container ─────────────────────────────────────
# Bind mounts:
#   ~/buem/src       → /app/src   (source code — PYTHONPATH is /app/src)
#   ~/buem_weather   → /data      (pipeline working directory)
#
# Environment variables passed into the container:
#   COSMO_WORK_DIR   — points to /data inside the container
#   COSMO_NCORES     — inherits SLURM_CPUS_PER_TASK
#   COSMO_YEAR       — year to process (from host env or default)
#   COSMO_MONTHS     — months to process (from host env or default)
#
# --pwd $PWD is recommended by SURF to avoid symlink path resolution issues.
#
apptainer exec \
    --pwd $PWD \
    --bind "${SRC_DIR}:/app/src" \
    --bind "${WORK_DIR}:/data" \
    --env "COSMO_WORK_DIR=/data" \
    --env "COSMO_NCORES=${SLURM_CPUS_PER_TASK:-16}" \
    --env "COSMO_YEAR=${COSMO_YEAR:-2018}" \
    --env "COSMO_MONTHS=${COSMO_MONTHS:-01,02,03,04,05,06,07,08,09,10,11,12}" \
    --env "HDF5_USE_FILE_LOCKING=FALSE" \
    "${SIF_PATH}" \
    python -m buem.weather run "$@"

echo ""
echo "============================================================"
echo "Pipeline finished at $(date)"
echo "============================================================"
