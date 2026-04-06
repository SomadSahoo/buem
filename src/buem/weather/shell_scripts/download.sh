#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 — Download GRIB Files from DWD OpenData
# ──────────────────────────────────────────────────────────────────────────────
# Downloads compressed GRIB (.grb.bz2) files for all configured attributes
# and months via HTTPS (curl preferred, wget fallback).
# Skips files that already exist locally with the correct remote file size.
#
# Usage:
#   sbatch download.sh                     # SLURM submission (all months)
#   bash download.sh                       # interactive (all months)
#   COSMO_MONTHS="01" bash download.sh     # single-month test
#
# Snellius note: use the "staging" partition for data transfers.
# ──────────────────────────────────────────────────────────────────────────────

#SBATCH -J cosmo_download
#SBATCH -t 02:00:00
#SBATCH -p staging
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH -o slurm_download.%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# ── Source shared configuration ───────────────────────────────────────────
source "${COSMO_SCRIPTS_DIR:-${HOME}/buem/src/buem/weather/shell_scripts}/common.sh"

# Parse months into zero-padded array
IFS=',' read -ra _MONTHS <<< "${COSMO_MONTHS}"
MONTHS=()
for M in "${_MONTHS[@]}"; do
    MONTHS+=("$(printf "%02d" "$((10#$M))")")
done

mkdir -p "${COSMO_DOWNLOAD_DIR}"

_log_header "COSMO-REA6 Download"
echo "============================================================"

# ── Download function ─────────────────────────────────────────────────────
download_file() {
    local url="$1"
    local dest="$2"
    local fname
    fname="$(basename "$dest")"

    mkdir -p "$(dirname "$dest")"

    # Check if already downloaded with correct size
    if [ -f "$dest" ]; then
        local remote_size
        if command -v curl &>/dev/null; then
            remote_size=$(curl -sI "$url" | grep -i 'content-length' | awk '{print $2}' | tr -d '\r')
        fi
        if [ -n "${remote_size:-}" ]; then
            local local_size
            local_size=$(stat --printf="%s" "$dest" 2>/dev/null || stat -f "%z" "$dest" 2>/dev/null || echo "0")
            if [ "$local_size" = "$remote_size" ]; then
                echo "  [SKIP] ${fname} (size OK: ${local_size} bytes)"
                return 0
            fi
            echo "  [WARN] ${fname} size mismatch (local=${local_size}, remote=${remote_size}) — re-downloading"
        fi
    fi

    echo "  [GET]  ${fname}"
    local tmp_dest="${dest}.part.$$"

    if command -v curl &>/dev/null; then
        curl -C - -f -s -S -L -o "${tmp_dest}" "${url}" || {
            echo "  [FAIL] curl failed for ${fname}"
            rm -f "${tmp_dest}"
            return 1
        }
    elif command -v wget &>/dev/null; then
        wget -c -q -O "${tmp_dest}" "${url}" || {
            echo "  [FAIL] wget failed for ${fname}"
            rm -f "${tmp_dest}"
            return 1
        }
    else
        echo "  [FAIL] Neither curl nor wget available"
        return 1
    fi

    # Atomic move
    mv -f "${tmp_dest}" "${dest}"
    echo "  [DONE] ${fname} ($(stat --printf="%s" "$dest" 2>/dev/null || stat -f "%z" "$dest") bytes)"
}

# ── Main loop ─────────────────────────────────────────────────────────────
TOTAL=0
SKIPPED=0
FAILED=0

for ATTR in "${COSMO_ATTRS[@]}"; do
    ATTR_DIR="${COSMO_DOWNLOAD_DIR}/${ATTR}"
    mkdir -p "${ATTR_DIR}"

    for M in "${MONTHS[@]}"; do
        FNAME="${ATTR}.2D.${COSMO_YEAR}${M}.grb.bz2"
        URL="${COSMO_BASE_URL}/${ATTR}/${FNAME}"
        DEST="${ATTR_DIR}/${FNAME}"

        TOTAL=$((TOTAL + 1))
        if download_file "${URL}" "${DEST}"; then
            : # success or skip
        else
            FAILED=$((FAILED + 1))
        fi
    done
done

echo ""
echo "============================================================"
echo "Download complete at $(date)"
echo "  Total files:   ${TOTAL}"
echo "  Failed:        ${FAILED}"
echo "============================================================"

[ "${FAILED}" -eq 0 ] || exit 1
