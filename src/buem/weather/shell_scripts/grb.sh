#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 — Decompress-only (Snellius)
# ──────────────────────────────────────────────────────────────────────────────
# Decompresses all .grb.bz2 files that have already been downloaded.
# Uses lbzip2 / pbzip2 / bzip2 (auto-detected).
#
# Usage:
#   sbatch grb.sh                   # SLURM submission
#   bash grb.sh                     # interactive
# ──────────────────────────────────────────────────────────────────────────────

#SBATCH -J cosmo_decompress
#SBATCH -t 01:00:00
#SBATCH -p rome
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -o slurm_decompress.%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# ── Source shared configuration ───────────────────────────────────────────
source "${COSMO_SCRIPTS_DIR:-${HOME}/buem/src/buem/weather/shell_scripts}/common.sh"

DEC_CMD="$(_detect_decompressor)"

_log_header "COSMO-REA6 Decompression"
echo "  Decompressor: ${DEC_CMD}"
echo "============================================================"

for ATTR in "${COSMO_ATTRS[@]}"; do
    SRC="${COSMO_DOWNLOAD_DIR}/${ATTR}"
    DEST="${COSMO_DECOMPRESS_DIR}/${ATTR}"
    mkdir -p "${DEST}"

    echo ""
    echo "Processing ${ATTR}..."
    for bz2file in "${SRC}"/*.bz2; do
        [ -f "${bz2file}" ] || continue
        grbfile="${DEST}/$(basename "${bz2file%.bz2}")"
        if [ -f "${grbfile}" ] && [ -s "${grbfile}" ]; then
            echo "  [SKIP] $(basename "${grbfile}")"
            continue
        fi
        echo "  [DEC]  $(basename "${bz2file}")"
        case "${DEC_CMD}" in
            lbzip2)  lbzip2 -d -k -c -n "${COSMO_NCORES}" "${bz2file}" > "${grbfile}" ;;
            pbzip2)  pbzip2 -d -p"${COSMO_NCORES}" -c "${bz2file}" > "${grbfile}" ;;
            bzip2)   bzip2 -d -k -c "${bz2file}" > "${grbfile}" ;;
        esac
    done
    echo "Decompression for ${ATTR} finished at: $(date)"
done

echo ""
echo "============================================================"
echo "All decompression finished at: $(date)"
echo "============================================================"