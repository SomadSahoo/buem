Processing Pipeline
===================

The pipeline transforms raw COSMO-REA6 GRIB archives into a single
analysis-ready NetCDF-4 file in four steps.

.. code-block:: text

   DWD OpenData (.grb.bz2)
       │
       ▼  Step 1 — Download (HTTPS, parallel per attribute/month)
   download/
       │
       ▼  Step 2 — Decompress (lbzip2 / pbzip2 / Python bz2)
   decompress/
       │
       ▼  Step 3 — Transform (xarray + cfgrib, dask threaded)
   xarray.Dataset (in memory, chunked)
       │
       ▼  Step 4 — Export (NetCDF-4 with zlib, per-variable compute)
   output/COSMO_REA6_2018_Jan.nc


Step 1 — Download
-----------------

``download.py`` fetches compressed GRIB files from the DWD OpenData archive.

- One file per attribute per month (e.g. ``SWDIRS_RAD.2D.201801.grb.bz2``).
- **Idempotent**: compares local file size with remote ``Content-Length``
  before downloading; skips complete files.
- Supports HTTPS (default) with resume via ``Range`` header, and FTP fallback.
- Files are written atomically (to a temp file, then renamed).


Step 2 — Decompress
--------------------

``decompress.py`` extracts raw GRIB from ``.grb.bz2`` archives.

- Auto-detects the best available tool: ``lbzip2`` > ``pbzip2`` > Python ``bz2``.
- Parallel decompression across files using a thread pool.
- Atomic writes: a crash never leaves a half-written GRIB file.
- ``lbzip2`` is preferred because it scales better across multiple cores.


Step 3 — Transform
------------------

``transform.py`` reads decompressed GRIB files and produces an xarray
Dataset with analysis-ready variables.

**Raw attributes** (from COSMO-REA6):

.. list-table::
   :header-rows: 1

   * - Field
     - Description
     - Raw unit
   * - ``SWDIFDS_RAD``
     - Downward diffuse shortwave radiation at surface
     - W/m²
   * - ``SWDIRS_RAD``
     - Downward direct shortwave radiation at surface
     - W/m²
   * - ``T_2M``
     - Temperature at 2 m above ground
     - K
   * - ``U_10M``
     - U-component of wind at 10 m
     - m/s
   * - ``V_10M``
     - V-component of wind at 10 m
     - m/s

**Derived fields** (computed during transform):

.. list-table::
   :header-rows: 1

   * - Field
     - Formula
     - Unit
   * - ``GHI``
     - ``SWDIFDS_RAD + SWDIRS_RAD``
     - W/m²
   * - ``DHI``
     - ``SWDIFDS_RAD``
     - W/m²
   * - ``T``
     - ``T_2M − 273.15``
     - °C
   * - ``WS_10M``
     - :math:`\sqrt{U\_10M^2 + V\_10M^2}`
     - m/s

- Chunked processing with dask (``time=168``, ~1 week per chunk).
- Uses the **threaded scheduler** — all threads share the same memory space,
  avoiding the overhead and OOM risks of ``dask.distributed``.


Step 4 — Export
---------------

``export.py`` writes the Dataset to a compressed NetCDF-4 file.

- zlib compression (default level 1 — fastest; levels 2–9 give negligible
  size reduction at much higher CPU cost on the 824×848 COSMO grid).
- Variables are computed **one at a time** to cap peak memory at ~4 GiB
  instead of materialising all fields simultaneously.
- ``float32`` encoding halves file size without meaningful precision loss.

**Output naming convention**:

.. list-table::
   :header-rows: 1

   * - Months processed
     - Filename
   * - All 12 (full year)
     - ``COSMO_REA6_2018.nc``
   * - Single month
     - ``COSMO_REA6_2018_Jan.nc``
   * - Multiple months
     - ``COSMO_REA6_2018_Jan-Mar.nc``


Step 5 — Cleanup (optional)
----------------------------

When ``--cleanup`` is passed, the pipeline removes the ``download/`` and
``decompress/`` directories after a successful export.  The download and
decompression steps are fast enough that re-running them is inexpensive.


Memory and Performance
----------------------

The pipeline is tuned for a **1/8 node** allocation on Snellius
(16 cores, 28 GiB RAM):

- Dask threaded scheduler (no distributed workers).
- Chunk size ``time=168`` (~67 MB per chunk).
- Sequential per-variable export (peak ~4 GiB).
- Benchmark: ~7.5 minutes for 1 month of all 5 attributes.
