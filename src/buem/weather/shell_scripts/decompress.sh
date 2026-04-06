#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 — Streaming Download + Decompress (Snellius)
# ──────────────────────────────────────────────────────────────────────────────
# Downloads .grb.bz2 files from DWD and decompresses them in parallel as each
# download finishes.  This is faster than download-all-then-decompress because
# decompression overlaps with download I/O.
#
# Usage:
#   sbatch decompress.sh                  # SLURM — all months
#   COSMO_MONTHS="01,02" sbatch decompress.sh  # specific months
#   bash decompress.sh                    # interactive
# ──────────────────────────────────────────────────────────────────────────────

#SBATCH -J cosmo_dl_decompress
#SBATCH -t 04:00:00
#SBATCH -p rome
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -o slurm_dl_decompress.%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# ── Source shared configuration ───────────────────────────────────────────
source "${COSMO_SCRIPTS_DIR:-${HOME}/buem/src/buem/weather/shell_scripts}/common.sh"

# ── Derived settings ─────────────────────────────────────────────────────
if [ "${COSMO_THREADS_PER_JOB}" -gt "${COSMO_NCORES}" ]; then
    COSMO_THREADS_PER_JOB=1
fi
CONCURRENT_JOBS=$((COSMO_NCORES / COSMO_THREADS_PER_JOB))
if [ "${CONCURRENT_JOBS}" -lt 1 ]; then CONCURRENT_JOBS=1; COSMO_THREADS_PER_JOB=1; fi

# Parse months into zero-padded array
IFS=',' read -ra _MONTHS <<< "${COSMO_MONTHS}"
MONTHS_PADDED=()
for M in "${_MONTHS[@]}"; do
    MONTHS_PADDED+=("$(printf "%02d" "$((10#$M))")")
done

DEC_CMD="$(_detect_decompressor)"

_log_header "COSMO-REA6 Streaming Download + Decompress"
echo "  Decompressor: ${DEC_CMD}"
echo "  Concurrency:  ${CONCURRENT_JOBS} jobs × ${COSMO_THREADS_PER_JOB} threads"
echo "============================================================"

mkdir -p "${COSMO_DOWNLOAD_DIR}" "${COSMO_DECOMPRESS_DIR}"

# ── Helper functions ──────────────────────────────────────────────────────
count_active_decompress_jobs() {
    local count=0
    for pid in $(jobs -rp); do
        if kill -0 "$pid" 2>/dev/null; then
            count=$((count + 1))
        fi
    done
    echo "$count"
}

decompress_one() {
    local bz2file="$1"
    local destfile="$2"

    if [ -f "${destfile}" ] && [ -s "${destfile}" ]; then
        echo "    [SKIP] $(basename "${destfile}")"
        return 0
    fi

    echo "    [DEC]  $(basename "${bz2file}")"
    case "${DEC_CMD}" in
        pbzip2) pbzip2 -d -p"${COSMO_THREADS_PER_JOB}" -c "${bz2file}" > "${destfile}" ;;
        lbzip2) lbzip2 -d -n "${COSMO_THREADS_PER_JOB}" -c "${bz2file}" > "${destfile}" ;;
        bzip2)  bzip2 -d -c "${bz2file}" > "${destfile}" ;;
    esac

    if [ ! -s "${destfile}" ]; then
        echo "    [WARN] Zero-size output: ${destfile}"
        rm -f "${destfile}"
    fi
}

download_and_decompress() {
    local url="$1"
    local dest="$2"
    local grb_dest="${dest%.bz2}"

    mkdir -p "$(dirname "${dest}")" "$(dirname "${grb_dest}")"

    # Already decompressed?
    if [ -f "${grb_dest}" ] && [ -s "${grb_dest}" ]; then
        echo "  [SKIP] Already decompressed: $(basename "${grb_dest}")"
        return 0
    fi

    # Download if needed
    if [ ! -f "${dest}" ]; then
        echo "  [DL]   $(basename "${dest}")"
        local tmp="${dest}.part.$$"
        if command -v curl >/dev/null 2>&1; then
            curl -C - -f -s -S -L -o "${tmp}" "${url}" || {
                echo "  [FAIL] curl failed for ${url}"
                rm -f "${tmp}"
                return 1
            }
        elif command -v wget >/dev/null 2>&1; then
            wget -c -q -O "${tmp}" "${url}" || {
                echo "  [FAIL] wget failed for ${url}"
                rm -f "${tmp}"
                return 1
            }
        else
            echo "  [FAIL] Neither curl nor wget available"
            return 1
        fi
        mv -f "${tmp}" "${dest}"
    fi

    # Decompress
    local attr_dec_dir
    attr_dec_dir="$(dirname "${grb_dest}")"
    mkdir -p "${attr_dec_dir}"

    # Wait for a decompression slot
    while [ "$(count_active_decompress_jobs)" -ge "${CONCURRENT_JOBS}" ]; do
        sleep 0.5
    done

    decompress_one "${dest}" "${grb_dest}" &
}

# ── Main loop ─────────────────────────────────────────────────────────────
for ATTR in "${COSMO_ATTRS[@]}"; do
    ATTR_DL_DIR="${COSMO_DOWNLOAD_DIR}/${ATTR}"
    ATTR_DEC_DIR="${COSMO_DECOMPRESS_DIR}/${ATTR}"
    mkdir -p "${ATTR_DL_DIR}" "${ATTR_DEC_DIR}"

    for M in "${MONTHS_PADDED[@]}"; do
        FNAME="${ATTR}.2D.${COSMO_YEAR}${M}.grb.bz2"
        URL="${COSMO_BASE_URL}/${ATTR}/${FNAME}"
        DEST="${ATTR_DL_DIR}/${FNAME}"
        GRB_DEST="${ATTR_DEC_DIR}/${ATTR}.2D.${COSMO_YEAR}${M}.grb"

        download_and_decompress "${URL}" "${DEST}" || true
    done
done

# Wait for all background decompressions to finish
wait

echo ""
echo "============================================================"
echo "Streaming download+decompress finished at $(date)"
echo "============================================================"
