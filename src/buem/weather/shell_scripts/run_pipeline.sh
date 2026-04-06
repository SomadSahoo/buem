#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 Weather Pipeline — SLURM Job (Snellius)
# ──────────────────────────────────────────────────────────────────────────────
# Runs download → decompress → transform → export on a single node.
#
# Usage:
#   sbatch run_pipeline.sh                           # full year, all months
#   sbatch run_pipeline.sh --months 1                # single-month test
#   sbatch run_pipeline.sh --skip-download --months 1 2 3
#
# Snellius partition guide (SURF):
#   rome   — 128 cores / 224 GiB (1/8 node = 16 cores + 28 GiB, 16 SBU/h)
#   genoa  — 192 cores / 336 GiB (1/8 node = 24 cores + 42 GiB)
#   thin   — same as rome
#
# If you only need to download data, use download.sh on the staging partition.
# ──────────────────────────────────────────────────────────────────────────────

#SBATCH -J cosmo_weather
#SBATCH -t 00:45:00
#SBATCH -p rome
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -o slurm_weather.%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# ── Source shared configuration ───────────────────────────────────────────
source "${COSMO_SCRIPTS_DIR:-${HOME}/buem/src/buem/weather/shell_scripts}/common.sh"

# ── Activate environment & PYTHONPATH ─────────────────────────────────────
_activate_conda_env
_setup_pythonpath

_log_header "COSMO-REA6 Weather Pipeline — SLURM Job"

# ── Run the pipeline ─────────────────────────────────────────────────────
echo ""
echo "Running: python -m buem.weather run $*"
echo ""

python -m buem.weather run "$@"

echo ""
echo "============================================================"
echo "Pipeline finished at $(date)"
echo "============================================================"
