#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# COSMO-REA6 Weather Pipeline — Container Build Script (deps-only)
# ──────────────────────────────────────────────────────────────────────────────
# Builds a deps-only container image (conda env + system tools).
# Source code is NOT baked in — it is bind-mounted at runtime.
# Rebuild only when weather_env.yml changes.
#
#   1. def      — Build Apptainer SIF from .def file on Snellius pbuild
#                 partition (recommended — everything stays on the server)
#   2. docker   — Build Docker image locally (requires Docker Desktop / Engine)
#   3. convert  — Convert local Docker image to Apptainer SIF (local only)
#   4. pull     — Pull Docker image from registry as Apptainer SIF
#                 (works on Snellius login node — no root needed)
#
# Recommended workflow — build directly on Snellius (pbuild partition):
#   SNELLIUS:  cd ~/buem
#              bash src/buem/weather/shell_scripts/build_container.sh def
#   This submits a SLURM batch job to the pbuild partition.
#   When the job completes, buem_weather.sif appears in ~/buem/.
#
# Alternative — Docker locally → registry → pull on Snellius:
#   LOCAL:     bash build_container.sh docker --push   # needs CONTAINER_REGISTRY
#   SNELLIUS:  bash build_container.sh pull             # on login node
#
# Alternative — build SIF locally → scp to Snellius:
#   LOCAL:     bash build_container.sh def              # needs root/sudo
#   LOCAL:     scp buem_weather.sif ssahoo@snellius.surf.nl:~/buem/
#
# Usage:
#   bash build_container.sh def                   # pbuild batch job (Snellius)
#   bash build_container.sh docker                # build Docker image locally
#   bash build_container.sh docker --push         # build + push to registry
#   bash build_container.sh convert               # Docker → SIF (local)
#   bash build_container.sh pull                  # registry → SIF (Snellius)
#
# Environment:
#   CONTAINER_REGISTRY   Docker registry (e.g. docker.io/somadsahoo)
#   CONTAINER_TAG        Image tag (default: latest)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve repository root (where the Dockerfile context is)
# shell_scripts/ → weather/ → buem/ → src/ → repo root  (4 levels up)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEATHER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

IMAGE_NAME="buem-weather"
TAG="${CONTAINER_TAG:-latest}"
REGISTRY="${CONTAINER_REGISTRY:-}"
SIF_NAME="buem_weather.sif"

METHOD="${1:-docker}"
PUSH_FLAG="${2:-}"

cd "${REPO_ROOT}"

echo "============================================================"
echo "COSMO-REA6 Weather Pipeline — Container Build"
echo "  Method:   ${METHOD}"
echo "  Context:  ${REPO_ROOT}"
echo "  Started:  $(date)"
echo "============================================================"

case "${METHOD}" in
    docker)
        FULL_IMAGE="${IMAGE_NAME}:${TAG}"
        if [ -n "${REGISTRY}" ]; then
            FULL_IMAGE="${REGISTRY}/${FULL_IMAGE}"
        fi

        echo "Building Docker image: ${FULL_IMAGE}"
        docker build \
            -f src/buem/weather/Dockerfile.weather \
            -t "${FULL_IMAGE}" \
            .

        echo ""
        echo "Docker image built: ${FULL_IMAGE}"

        if [ "${PUSH_FLAG}" = "--push" ]; then
            if [ -z "${REGISTRY}" ]; then
                echo "ERROR: Set CONTAINER_REGISTRY to push (e.g. docker.io/myuser)"
                exit 1
            fi
            echo "Pushing ${FULL_IMAGE} ..."
            docker push "${FULL_IMAGE}"
            echo ""
            echo "On Snellius, pull with:"
            echo "  apptainer pull docker://${FULL_IMAGE}"
        fi
        ;;

    def)
        DEF_FILE="${WEATHER_DIR}/weather.def"
        if [ ! -f "${DEF_FILE}" ]; then
            echo "ERROR: Definition file not found: ${DEF_FILE}"
            exit 1
        fi

        # Detect whether we are already inside a SLURM job (pbuild node).
        if [ -n "${SLURM_JOB_ID:-}" ]; then
            # Running on a pbuild compute node — build directly.
            # /scratch-local is a network mount that breaks fakeroot;
            # use /tmp and bind /dev/shm:/tmp as SURF recommends.
            export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-/tmp}"
            echo "Building Apptainer SIF from ${DEF_FILE}"
            echo "  APPTAINER_TMPDIR=${APPTAINER_TMPDIR}"
            apptainer build --fakeroot -B/dev/shm:/tmp "${SIF_NAME}" "${DEF_FILE}"
            echo ""
            echo "SIF image built: $(pwd)/${SIF_NAME}"
        else
            # On login node — submit a batch job to pbuild.
            echo "Submitting build job to pbuild partition..."
            sbatch --wait \
                -p pbuild \
                -t 2:00:00 \
                -J cosmo_build \
                -o slurm_build.%j.out \
                --wrap "cd ${REPO_ROOT} && export APPTAINER_TMPDIR=/tmp && apptainer build --fakeroot -B/dev/shm:/tmp ${SIF_NAME} ${DEF_FILE}"
            echo ""
            if [ -f "${SIF_NAME}" ]; then
                echo "SIF image built: $(pwd)/${SIF_NAME}"
            else
                echo "ERROR: Build may have failed. Check slurm_build.*.out for details."
                exit 1
            fi
        fi
        ;;

    convert)
        FULL_IMAGE="${IMAGE_NAME}:${TAG}"
        if [ -n "${REGISTRY}" ]; then
            FULL_IMAGE="${REGISTRY}/${FULL_IMAGE}"
        fi

        echo "Converting Docker image ${FULL_IMAGE} → ${SIF_NAME}"
        apptainer build "${SIF_NAME}" "docker-daemon:${FULL_IMAGE}"
        echo ""
        echo "SIF image built: $(pwd)/${SIF_NAME}"
        echo "  Copy to Snellius:  scp ${SIF_NAME} ssahoo@snellius.surf.nl:~/buem/"
        ;;

    pull)
        if [ -z "${REGISTRY}" ]; then
            echo "ERROR: Set CONTAINER_REGISTRY to pull (e.g. docker.io/myuser)"
            exit 1
        fi
        FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${TAG}"

        echo "Pulling ${FULL_IMAGE} → ${SIF_NAME}"
        apptainer pull --name "${SIF_NAME}" "docker://${FULL_IMAGE}"
        echo ""
        echo "SIF image ready: $(pwd)/${SIF_NAME}"
        ;;

    *)
        echo "Usage: $0 {docker|def|convert|pull} [--push]"
        echo ""
        echo "Methods:"
        echo "  docker   — Build Docker image locally (can push to registry)"
        echo "  def      — Build Apptainer SIF from weather.def (Snellius pbuild / local with root)"
        echo "  convert  — Convert local Docker image to SIF (local)"
        echo "  pull     — Pull Docker image from registry as SIF (Snellius login node)"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "Build finished at $(date)"
echo "============================================================"
