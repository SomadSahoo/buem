"""End-to-end COSMO-REA6 weather processing pipeline.

Orchestrates the full workflow:

    1. **Download** — fetch ``.grb.bz2`` files from DWD OpenData.
    2. **Decompress** — parallel bz2 decompression to raw GRIB.
    3. **Transform** — read GRIB with xarray/cfgrib, convert units,
       compute derived fields (GHI, DHI, T, WS_10M).
    4. **Export** — write a single compressed NetCDF-4 file.

Each step is idempotent: re-running skips files that are already present and
have the expected size.

Typical usage (from Python)::

    from buem.weather.pipeline import run_pipeline
    nc_path = run_pipeline(year=2018, months=[1])  # single-month test

From the CLI::

    buem weather run --year 2018 --months 1
    buem weather run                          # full year (all months)
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Prevent HDF5 file-locking deadlocks on network/parallel file systems (GPFS).
os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")


def run_pipeline(
    year: int | None = None,
    months: list[int] | None = None,
    attributes: list[str] | None = None,
    *,
    work_dir: Path | None = None,
    output_path: Path | None = None,
    include_wind_components: bool = True,
    complevel: int = 1,
    skip_download: bool = False,
    skip_decompress: bool = False,
) -> Path:
    """Execute the full weather processing pipeline.

    Parameters
    ----------
    year : int, optional
        Target year (default from config: 2018).
    months : list[int], optional
        Months to process (default from config: 1–12).
        For a quick test run, pass ``[1]`` for January only.
    attributes : list[str], optional
        COSMO-REA6 attributes (default: all five).
    work_dir : Path, optional
        Override the root working directory.
    output_path : Path, optional
        Override the output NetCDF file path.
    include_wind_components : bool
        Keep raw U_10M / V_10M in the NetCDF (default ``True``).
    complevel : int
        zlib compression level for NetCDF (default 5).
    skip_download : bool
        Skip downloading (assume ``.grb.bz2`` files already present).
    skip_decompress : bool
        Skip decompression (assume ``.grb`` files already present).

    Returns
    -------
    Path
        Path to the output NetCDF file.
    """
    from .config import get_config
    from .decompress import decompress_all
    from .download import download_all
    from .export import export_netcdf
    from .transform import build_annual_dataset

    cfg = get_config()
    year = year or cfg["year"]
    months = months or cfg["months"]
    attributes = attributes or cfg["attributes"]

    # Allow work_dir override
    if work_dir:
        import os
        os.environ["COSMO_WORK_DIR"] = str(work_dir)
        cfg = get_config()  # re-resolve

    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info("COSMO-REA6 Weather Pipeline")
    logger.info("  Year:       %d", year)
    logger.info("  Months:     %s", months)
    logger.info("  Attributes: %s", attributes)
    logger.info("  Work dir:   %s", cfg["work_dir"])
    logger.info("=" * 60)

    # Step 1: Download
    if not skip_download:
        logger.info("STEP 1/4: Downloading GRIB files")
        t1 = time.perf_counter()
        download_all(year=year, months=months, attributes=attributes)
        logger.info("  Download completed in %.1f s", time.perf_counter() - t1)
    else:
        logger.info("STEP 1/4: Download skipped (--skip-download)")

    # Step 2: Decompress
    if not skip_decompress:
        logger.info("STEP 2/4: Decompressing GRIB files")
        t2 = time.perf_counter()
        decompress_all(
            attributes=attributes, year=year, months=months,
        )
        logger.info("  Decompress completed in %.1f s", time.perf_counter() - t2)
    else:
        logger.info("STEP 2/4: Decompress skipped (--skip-decompress)")

    # Step 3: Transform
    logger.info("STEP 3/4: Transforming to analysis-ready variables")
    t3 = time.perf_counter()
    ds = build_annual_dataset(
        year=year,
        months=months,
        include_wind_components=include_wind_components,
    )
    logger.info("  Transform completed in %.1f s", time.perf_counter() - t3)

    # Step 4: Export
    logger.info("STEP 4/4: Exporting to NetCDF")
    t4 = time.perf_counter()
    nc_path = export_netcdf(ds, output_path=output_path, complevel=complevel, year=year)
    logger.info("  Export completed in %.1f s", time.perf_counter() - t4)

    elapsed = time.perf_counter() - t0
    logger.info("=" * 60)
    logger.info("Pipeline complete: %s (%.1f s total)", nc_path, elapsed)
    logger.info("=" * 60)

    return nc_path


def validate_environment() -> list[str]:
    """Check that all required tools and libraries are available.

    Returns
    -------
    list[str]
        List of issues found (empty = all OK).
    """
    issues: list[str] = []

    # Python packages
    for pkg in ("xarray", "cfgrib", "netCDF4", "pyproj", "eccodes"):
        try:
            __import__(pkg)
        except ImportError:
            issues.append(
                f"Python package '{pkg}' not installed.  "
                f"Install with: conda install conda-forge::{pkg}"
            )

    # External decompressors (optional but recommended)
    import shutil
    for cmd in ("pbzip2", "lbzip2"):
        if shutil.which(cmd):
            break
    else:
        issues.append(
            "No parallel decompressor found (pbzip2 or lbzip2).  "
            "The Python bz2 fallback is much slower.  "
            "Install with: conda install conda-forge::pbzip2"
        )

    # Config sanity
    from .config import get_config
    cfg = get_config()
    if not cfg["months"]:
        issues.append("COSMO_MONTHS is empty; no months to process.")
    if cfg["year"] < 1995 or cfg["year"] > 2019:
        issues.append(
            f"COSMO_YEAR={cfg['year']} is outside COSMO-REA6 range (1995–2019)."
        )

    return issues
