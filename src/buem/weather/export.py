"""Export processed COSMO-REA6 data to compressed NetCDF.

Writes the annual :class:`xarray.Dataset` produced by
:func:`~buem.weather.transform.build_annual_dataset` to a single NetCDF-4
file with zlib compression, following CF-1.8 conventions.

Typical usage::

    from buem.weather.export import export_netcdf
    export_netcdf(ds, Path("/data/output/COSMO_REA6_2018.nc"))
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd  # noqa: F401
    import xarray  # noqa: F401  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Prevent HDF5 file-locking deadlocks on network/parallel file systems (GPFS).
os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")


def _build_encoding(ds: xarray.Dataset, complevel: int = 1) -> dict:
    """Build per-variable NetCDF encoding with zlib compression.

    Parameters
    ----------
    ds : xarray.Dataset
        The dataset to encode.
    complevel : int
        zlib compression level (1=fastest, 9=smallest; 1 is recommended
        because levels 2–9 give diminishing returns for much higher CPU
        cost on large grids like COSMO-REA6 824×848).

    Returns
    -------
    dict
        Encoding dict suitable for :meth:`xarray.Dataset.to_netcdf`.
    """
    encoding = {}
    for var in ds.data_vars:
        encoding[var] = {
            "zlib": True,
            "complevel": complevel,
            # Use float32 for radiation/temperature/wind to halve file size
            # without meaningful precision loss (instruments are ~0.1 W/m²).
            "dtype": "float32",
        }
    return encoding


def export_netcdf(
    ds: xarray.Dataset,
    output_path: Path | None = None,
    *,
    complevel: int = 1,
    year: int | None = None,
    months: list[int] | None = None,
) -> Path:
    """Write the processed dataset to a compressed NetCDF-4 file.

    Parameters
    ----------
    ds : xarray.Dataset
        Processed annual weather dataset.
    output_path : Path, optional
        Full path for the output file.  If omitted, defaults to
        ``<work_dir>/output/COSMO_REA6_<year>.nc`` for a full year, or
        ``<work_dir>/output/COSMO_REA6_<year>_Jan.nc`` for a single month.
    complevel : int
        zlib compression level (default 1 — fastest; levels 2–9 give
        minimal size reduction for much higher CPU cost on large grids).
    year : int, optional
        Year label for the default filename.
    months : list[int], optional
        Months being processed — used for filename generation.

    Returns
    -------
    Path
        Path to the written NetCDF file.
    """
    if output_path is None:
        import calendar

        from .config import get_config
        cfg = get_config()
        yr = year or cfg["year"]
        mo = months or cfg["months"]
        if len(mo) == 12:
            # Full year → COSMO_REA6_2018.nc
            fname = f"COSMO_REA6_{yr}.nc"
        elif len(mo) == 1:
            # Single month → COSMO_REA6_2018_Jan.nc
            month_abbr = calendar.month_abbr[mo[0]]
            fname = f"COSMO_REA6_{yr}_{month_abbr}.nc"
        else:
            # Multiple months → COSMO_REA6_2018_Jan-Mar.nc
            first = calendar.month_abbr[mo[0]]
            last = calendar.month_abbr[mo[-1]]
            fname = f"COSMO_REA6_{yr}_{first}-{last}.nc"
        output_path = cfg["output_dir"] / fname

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Materialise dask arrays into in-memory arrays BEFORE writing.
    # Compute one variable at a time to limit peak memory usage —
    # loading all variables simultaneously would require ~12 GiB,
    # but sequential computation peaks at ~4 GiB per variable.
    import time
    t0 = time.perf_counter()
    logger.info("Computing dask arrays into memory (variable-by-variable)...")
    for var_name in list(ds.data_vars):
        if hasattr(ds[var_name].data, "dask"):
            logger.info("  Computing %s ...", var_name)
            ds[var_name] = ds[var_name].compute()
    logger.info("  All variables computed in %.1f s", time.perf_counter() - t0)

    encoding = _build_encoding(ds, complevel=complevel)
    logger.info("Writing NetCDF to %s (complevel=%d)", output_path, complevel)

    t1 = time.perf_counter()
    ds.to_netcdf(
        output_path,
        encoding=encoding,
        format="NETCDF4",
        engine="netcdf4",
    )
    logger.info("  NetCDF write done in %.1f s", time.perf_counter() - t1)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("NetCDF written: %s (%.1f MB)", output_path.name, size_mb)
    return output_path


def export_single_point_csv(
    ds: xarray.Dataset,
    rlat_idx: int,
    rlon_idx: int,
    output_path: Path,
) -> Path:
    """Extract a single grid-cell time series and write to CSV.

    Useful for extracting weather data for a specific building location
    in the format expected by :class:`~buem.weather.from_csv.CsvWeatherData`.

    Parameters
    ----------
    ds : xarray.Dataset
        Processed annual dataset (must contain ``T``, ``GHI``, ``DHI``).
    rlat_idx, rlon_idx : int
        Grid indices (0-based) in the rotated-pole grid.
    output_path : Path
        Output CSV file path.

    Returns
    -------
    Path
        Path to the written CSV.

    Notes
    -----
    The output CSV contains columns ``T``, ``GHI``, ``DHI`` matching the
    format expected by :class:`~buem.weather.from_csv.CsvWeatherData`.
    DNI must be reconstructed by the thermal model using pvlib DISC from GHI.
    """
    import pandas as pd  # noqa: F811

    logger.info(
        "Extracting single point (rlat=%d, rlon=%d) to %s",
        rlat_idx, rlon_idx, output_path,
    )

    point = ds.isel(y=rlat_idx, x=rlon_idx)

    df = pd.DataFrame(
        {
            "T": point["T"].values,
            "GHI": point["GHI"].values,
            "DHI": point["DHI"].values,
        },
        index=pd.to_datetime(point["time"].values, utc=True),
    )
    df.index.name = "datetime"

    # Add WS_10M if present
    if "WS_10M" in point:
        df["WS_10M"] = point["WS_10M"].values

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)
    logger.info("Single-point CSV written: %s (%d rows)", output_path.name, len(df))
    return output_path
