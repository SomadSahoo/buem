CLI Reference
=============

The weather pipeline is accessible via two equivalent entry points:

- ``buem weather <action>`` — when BuEM is installed (``pip install -e .``).
- ``python -m buem.weather <action>`` — standalone on servers without a full install.

Both accept the same arguments.


Actions
-------

``info`` — Show Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Print the resolved pipeline configuration (paths, year, months, attributes,
number of cores)::

    buem weather info

``validate`` — Check Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify that required Python packages and decompression tools are available::

    buem weather validate

``run`` — Execute Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the full download → decompress → transform → export pipeline::

    buem weather run                          # full year, all months
    buem weather run --months 1               # January only
    buem weather run --months 1 2 3           # Jan–Mar
    buem weather run --year 2017              # different year
    buem weather run --skip-download          # assume .grb.bz2 already exist
    buem weather run --skip-decompress        # assume .grb already exist
    buem weather run --cleanup                # remove intermediate files after export
    buem weather run --complevel 5            # zlib compression level (default: 5)
    buem weather run --no-wind-components     # exclude raw U_10M/V_10M
    buem weather run --work-dir /scratch/wx   # override working directory
    buem weather run --output /tmp/result.nc  # override output path


Options
-------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Flag
     - Description
     - Default
   * - ``--year``
     - Year to process
     - ``COSMO_YEAR`` or 2018
   * - ``--months``
     - Month number(s) to process
     - All 12
   * - ``--work-dir``
     - Override ``COSMO_WORK_DIR``
     - ``~/buem_weather``
   * - ``--output``
     - Override output NetCDF path
     - Auto-generated
   * - ``--complevel``
     - zlib compression level (1–9)
     - 5
   * - ``--skip-download``
     - Skip Step 1 (files must exist)
     - off
   * - ``--skip-decompress``
     - Skip Step 2 (files must exist)
     - off
   * - ``--cleanup``
     - Remove download + decompress dirs after export
     - off
   * - ``--no-wind-components``
     - Exclude raw U_10M / V_10M from output
     - off


Configuration via Environment
------------------------------

All settings can be controlled through environment variables or a ``.env``
file.  CLI flags take precedence.

.. list-table::
   :header-rows: 1

   * - Variable
     - Description
     - Default
   * - ``COSMO_WORK_DIR``
     - Base working directory
     - ``~/buem_weather``
   * - ``COSMO_YEAR``
     - Year to process
     - ``2018``
   * - ``COSMO_MONTHS``
     - Comma-separated months
     - ``01,02,...,12``
   * - ``COSMO_BASE_URL``
     - DWD archive URL
     - ``https://opendata.dwd.de/...``
   * - ``COSMO_NCORES``
     - Number of CPU cores
     - ``SLURM_CPUS_PER_TASK`` or ``os.cpu_count()``
   * - ``COSMO_DECOMPRESSOR``
     - Force a specific decompressor
     - Auto-detect
