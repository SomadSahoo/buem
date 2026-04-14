Container Deployment
====================

The weather pipeline runs inside a container on HPC clusters (Apptainer)
and VMs/workstations (Docker).  The image contains **only** the conda
environment and system tools — source code is bind-mounted at runtime.

This means:

- **Code changes** require only an ``scp`` and re-run (seconds).
- **Dependency changes** (``weather_env.yml``) require an image rebuild (~10 min).

Image Contents
--------------

.. list-table::
   :header-rows: 1

   * - Layer
     - What
   * - Base
     - ``continuumio/miniconda3:latest``
   * - System tools
     - ``lbzip2``, ``curl``
   * - Conda env
     - ``weather_env`` from ``weather_env.yml``
       (xarray, cfgrib, dask, netCDF4, eccodes, pvlib, etc.)
   * - Source code
     - **Not included** — bind-mounted at runtime


Apptainer (HPC / Snellius)
--------------------------

**Build** (only when ``weather_env.yml`` changes)::

    cd ~/buem
    bash src/buem/weather/shell_scripts/build_container.sh def

This submits a SLURM job to the ``pbuild`` partition.  The SIF image
appears at ``~/buem/buem_weather.sif`` when the job finishes.

**Run**::

    sbatch src/buem/weather/shell_scripts/run_pipeline_container.sh --months 1

The run script bind-mounts:

.. list-table::
   :header-rows: 1

   * - Host path
     - Container path
     - Purpose
   * - ``~/buem/src``
     - ``/app/src``
     - Python source code
   * - ``~/buem_weather``
     - ``/data``
     - Download, decompress, and output directories

**Update code without rebuilding**::

    # From local machine:
    scp -r src/buem/weather ssahoo@snellius.surf.nl:~/buem/src/buem/

    # On Snellius:
    sbatch src/buem/weather/shell_scripts/run_pipeline_container.sh --months 1

**Interactive debugging**::

    apptainer shell --bind ~/buem/src:/app/src ~/buem/buem_weather.sif
    # Inside the container:
    python -m buem.weather info
    python -m buem.weather validate

**Environment variables** (override defaults):

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``COSMO_SIF_PATH``
     - ``~/buem/buem_weather.sif``
     - Path to the SIF image
   * - ``COSMO_WORK_DIR``
     - ``~/buem_weather``
     - Host data directory
   * - ``COSMO_SRC_DIR``
     - ``~/buem/src``
     - Host source directory


Docker (VMs / Workstations)
---------------------------

**Build**::

    docker build -f src/buem/weather/Dockerfile.weather -t buem-weather .

**Run** (mount source + data)::

    docker run --rm \
        -v $(pwd)/src:/app/src \
        -v ~/buem_weather:/data \
        -e COSMO_WORK_DIR=/data \
        buem-weather \
        python -m buem.weather run --months 1

**Push to registry** (for ``apptainer pull`` on HPC)::

    docker tag buem-weather docker.io/<user>/buem-weather:latest
    docker push docker.io/<user>/buem-weather:latest


Build Methods
-------------

``build_container.sh`` supports four methods:

.. list-table::
   :header-rows: 1

   * - Method
     - Command
     - Where
   * - ``def``
     - Build SIF from ``weather.def``
     - Snellius (pbuild) or local with root
   * - ``docker``
     - Build Docker image
     - Local (Docker required)
   * - ``convert``
     - Docker image → SIF
     - Local (Apptainer required)
   * - ``pull``
     - Registry → SIF
     - Snellius login node (no root)


Key Files
---------

.. list-table::
   :header-rows: 1

   * - File
     - Purpose
   * - ``weather.def``
     - Apptainer definition (deps-only image)
   * - ``Dockerfile.weather``
     - Docker multi-stage build (deps-only image)
   * - ``shell_scripts/build_container.sh``
     - Build script (4 methods)
   * - ``shell_scripts/run_pipeline_container.sh``
     - SLURM job script for containerised runs
   * - ``weather_env.yml``
     - Conda environment specification
