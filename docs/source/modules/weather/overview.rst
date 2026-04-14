Module Overview
===============

The weather package is organised into focused, single-responsibility modules.
Each step of the pipeline is a separate file that can be imported and used
independently.

.. list-table::
   :header-rows: 1
   :widths: 20 55 25

   * - File
     - Purpose
     - Key function(s)
   * - ``config.py``
     - Centralised configuration from environment variables (``COSMO_*``).
       Attribute definitions, URL builders, path resolution.
     - ``get_config()``, ``ATTRIBUTES``
   * - ``download.py``
     - Fetch ``.grb.bz2`` files from DWD OpenData via HTTPS (with resume)
       or FTP fallback.  Skips already-downloaded files.
     - ``download_all()``, ``download_attribute_month()``
   * - ``decompress.py``
     - Parallel bz2 decompression using ``lbzip2``, ``pbzip2``, or Python
       ``bz2`` fallback.  Atomic writes prevent half-written files.
     - ``decompress_all()``, ``decompress_file()``
   * - ``transform.py``
     - Read GRIB with xarray + cfgrib, convert units (K → °C), compute
       derived fields (GHI, DHI, WS_10M).  Chunked via dask (threaded
       scheduler).
     - ``build_annual_dataset()``, ``open_grib_month()``
   * - ``export.py``
     - Write a compressed NetCDF-4 file with zlib encoding.  Sequential
       per-variable compute to limit memory.
     - ``export_netcdf()``
   * - ``pipeline.py``
     - End-to-end orchestrator chaining all four steps.  Optional cleanup
       of intermediate files.
     - ``run_pipeline()``, ``validate_environment()``
   * - ``from_csv.py``
     - Load pre-extracted single-point CSV weather files (T, GHI, DNI, DHI).
       Reconstructs physically-consistent DNI via pvlib DISC decomposition.
     - ``CsvWeatherData``
   * - ``__main__.py``
     - Standalone CLI entry point (``python -m buem.weather``).  Mirrors
       the ``buem weather`` CLI for server use.
     - ``main()``
   * - ``__init__.py``
     - Package docstring and public API surface.
     -


Standalone Usage
----------------

The weather package does **not** depend on the rest of BuEM.  It can run
on a remote server where only the ``src/buem/weather/`` directory and
``src/buem/__init__.py`` are present::

    # Copy to server
    scp -r src/buem ssahoo@server:~/buem/src/buem/

    # Run directly (no pip install needed — PYTHONPATH only)
    export PYTHONPATH=~/buem/src
    python -m buem.weather info
    python -m buem.weather run --months 1

When installed via ``pip install -e .``, the same functionality is available
through the unified CLI::

    buem weather info
    buem weather run --months 1
