"""Transform raw COSMO-REA6 GRIB fields into analysis-ready variables.

This module reads decompressed GRIB files with :mod:`xarray` + ``cfgrib``
engine, applies unit conversions, computes derived fields (GHI, DHI, WS_10M),
and merges everything into a single :class:`xarray.Dataset` with the
COSMO-REA6 rotated-pole coordinates plus auxiliary WGS84 lat/lon.

Key conversions (units matched to :class:`~buem.thermal.model_buem.ModelBUEM`):

+--------------+----------------+----------------+----------------------------------+
| Field        | Raw unit       | Target unit    | Formula                          |
+==============+================+================+==================================+
| T            | K              | °C             | T_2M - 273.15                    |
| GHI          | W/m²           | W/m²           | SWDIFDS_RAD + SWDIRS_RAD         |
| DHI          | W/m²           | W/m²           | SWDIFDS_RAD (diffuse component)  |
| WS_10M       | m/s            | m/s            | sqrt(U_10M² + V_10M²)           |
+--------------+----------------+----------------+----------------------------------+

DNI is intentionally **not** computed on the server grid because
``DNI = SWDIRS_RAD / cos(θ_z)`` diverges near the horizon.  The thermal model
already derives DNI per-building using pvlib's DISC decomposition from GHI,
which is numerically stable (see :meth:`from_csv.CsvWeatherData.reconstruct_dni_from_ghi`).

Typical usage::

    from buem.weather.transform import open_grib_month, build_annual_dataset
    ds_jan = open_grib_month("SWDIRS_RAD", 2018, 1)
    ds_year = build_annual_dataset(2018)
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import xarray  # noqa: F401  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def _import_xarray():
    """Lazy-import xarray (heavy dependency, not needed at module level)."""
    try:
        import xarray as xr  # noqa: F811  # type: ignore[import-untyped]
        return xr
    except ImportError as exc:
        raise ImportError(
            "xarray is required for weather transformation.  "
            "Install with: conda install conda-forge::xarray"
        ) from exc


# ---------------------------------------------------------------------------
# GRIB reading
# ---------------------------------------------------------------------------

def open_grib_month(
    attribute: str,
    year: int,
    month: int,
    *,
    grb_dir: Path | None = None,
) -> xarray.Dataset:
    """Open a single monthly GRIB file as an xarray Dataset.

    Parameters
    ----------
    attribute : str
        COSMO-REA6 attribute name (e.g. ``"T_2M"``).
    year, month : int
        Target period.
    grb_dir : Path, optional
        Directory containing decompressed ``.grb`` files (per-attribute sub-dirs).
        Defaults to ``<work_dir>/decompress/<attribute>/``.

    Returns
    -------
    xarray.Dataset
        Dataset with dimensions ``(time, y, x)`` in native rotated-pole
        coordinates.
    """
    xr = _import_xarray()
    from .config import get_config

    cfg = get_config()
    if grb_dir is None:
        grb_dir = cfg["decompress_dir"] / attribute

    grb_name = f"{attribute}.2D.{year}{month:02d}.grb"
    grb_path = grb_dir / grb_name

    if not grb_path.exists():
        raise FileNotFoundError(f"GRIB file not found: {grb_path}")

    logger.info("Opening GRIB: %s", grb_path)
    ds = xr.open_dataset(
        grb_path,
        engine="cfgrib",
        chunks={"time": 168},  # ~1 week per chunk; balances parallelism vs overhead
    )
    return ds


def open_grib_year(
    attribute: str,
    year: int,
    months: list[int] | None = None,
    *,
    grb_dir: Path | None = None,
) -> xarray.Dataset:
    """Open and concatenate all monthly GRIB files for one attribute/year.

    Uses :func:`xarray.open_mfdataset` with ``parallel=True`` for
    concurrent I/O across months via dask.delayed.

    Parameters
    ----------
    attribute : str
        COSMO-REA6 attribute name.
    year : int
        Target year.
    months : list[int], optional
        Months to load (default: from config).
    grb_dir : Path, optional
        Root directory for decompressed GRIBs.

    Returns
    -------
    xarray.Dataset
        Concatenated along the ``time`` dimension.
    """
    xr = _import_xarray()
    from .config import get_config

    cfg = get_config()
    months = months or cfg["months"]
    if grb_dir is None:
        grb_dir = cfg["decompress_dir"]

    attr_dir = grb_dir / attribute
    paths = []
    for m in sorted(months):
        p = attr_dir / f"{attribute}.2D.{year}{m:02d}.grb"
        if not p.exists():
            raise FileNotFoundError(f"GRIB file not found: {p}")
        paths.append(str(p))

    logger.info("Opening %d GRIB files for %s (parallel=True)", len(paths), attribute)
    combined = xr.open_mfdataset(
        paths,
        engine="cfgrib",
        combine="nested",
        concat_dim="time",
        parallel=True,
        chunks={"time": 168},    # ~1 week per chunk; fits in memory while allowing parallelism
        compat="override",
        coords="minimal",
        data_vars="minimal",
    )
    logger.info(
        "Loaded %s for %d: %d timesteps, grid %s",
        attribute, year, combined.sizes["time"],
        "x".join(str(s) for s in combined.sizes.values()),
    )
    return combined


# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------

def convert_temperature(ds: xarray.Dataset, var_name: str = "t2m") -> xarray.DataArray:
    """Convert temperature from Kelvin to Celsius.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing the temperature variable.
    var_name : str
        Name of the temperature variable in the dataset (cfgrib default: ``"t2m"``).

    Returns
    -------
    xarray.DataArray
        Temperature in °C.
    """
    da = ds[var_name]
    # cfgrib may already decode to °C if the GRIB edition supports it;
    # guard against double-conversion.
    # Check a single grid point to avoid computing max() over the entire
    # dask array, which would materialise the full dataset in memory and
    # OOM-kill distributed workers.
    sample = float(da.values.flat[0]) if hasattr(da.values, 'flat') else float(da.isel({d: 0 for d in da.dims}).values)
    if sample > 100:  # clearly Kelvin (typical range 230–320 K)
        logger.info("Converting T_2M from Kelvin to Celsius (sample=%.1f K)", sample)
        da = da - 273.15
        da.attrs["units"] = "degC"
    else:
        logger.info("T_2M appears to already be in Celsius (sample=%.1f)", sample)
        da.attrs["units"] = "degC"
    da.attrs["long_name"] = "Temperature at 2m"
    return da


def compute_ghi(
    ds_diffuse: xarray.Dataset,
    ds_direct: xarray.Dataset,
    diffuse_var: str = "SWDIFDS_RAD",
    direct_var: str = "SWDIRS_RAD",
) -> xarray.DataArray:
    """Compute Global Horizontal Irradiance: GHI = diffuse + direct.

    Parameters
    ----------
    ds_diffuse : xarray.Dataset
        Dataset with the SWDIFDS_RAD field.
    ds_direct : xarray.Dataset
        Dataset with the SWDIRS_RAD field.
    diffuse_var, direct_var : str
        Variable names inside the datasets.  cfgrib sometimes lowercases
        or uses short_name; the function tries common alternatives.

    Returns
    -------
    xarray.DataArray
        GHI in W/m².

    Notes
    -----
    Both inputs are clipped to ``[0, ∞)`` before summing — negative
    irradiance (rare GRIB artefact) is physically impossible.
    """
    diffuse = _resolve_var(ds_diffuse, diffuse_var)
    direct = _resolve_var(ds_direct, direct_var)

    ghi = diffuse.clip(min=0) + direct.clip(min=0)
    ghi.attrs = {"units": "W/m2", "long_name": "Global Horizontal Irradiance"}
    return ghi


def compute_dhi(
    ds_diffuse: xarray.Dataset,
    diffuse_var: str = "SWDIFDS_RAD",
) -> xarray.DataArray:
    """Extract Diffuse Horizontal Irradiance: DHI = SWDIFDS_RAD.

    Parameters
    ----------
    ds_diffuse : xarray.Dataset
        Dataset with the diffuse radiation field.
    diffuse_var : str
        Variable name.

    Returns
    -------
    xarray.DataArray
        DHI in W/m².
    """
    dhi = _resolve_var(ds_diffuse, diffuse_var).clip(min=0)
    dhi.attrs = {"units": "W/m2", "long_name": "Diffuse Horizontal Irradiance"}
    return dhi


def compute_wind_speed(
    ds_u: xarray.Dataset,
    ds_v: xarray.Dataset,
    u_var: str = "u10",
    v_var: str = "v10",
) -> xarray.DataArray:
    """Compute scalar wind speed: WS = sqrt(U² + V²).

    The magnitude is identical in both the rotated-pole and WGS84
    coordinate systems, so no vector rotation is needed for this
    derived quantity.

    Parameters
    ----------
    ds_u, ds_v : xarray.Dataset
        Datasets with U and V wind components.
    u_var, v_var : str
        Variable names.

    Returns
    -------
    xarray.DataArray
        Wind speed at 10 m in m/s.
    """
    xr = _import_xarray()
    u = _resolve_var(ds_u, u_var)
    v = _resolve_var(ds_v, v_var)
    ws: xarray.DataArray = xr.DataArray(
        np.sqrt(u ** 2 + v ** 2),
        coords=u.coords,
        dims=u.dims,
        attrs={"units": "m/s", "long_name": "Wind speed at 10m"},
    )
    return ws


def _strip_scalar_coords(da: xarray.DataArray) -> xarray.DataArray:
    """Drop all non-dimension scalar coordinates from a DataArray.

    cfgrib attaches scalar coordinates like ``heightAboveGround``, ``step``,
    ``surface``, and ``valid_time`` to each dataset.  These values differ
    across variables (e.g. T_2M has ``heightAboveGround=2``, wind has
    ``heightAboveGround=10``, radiation has none) and cause
    ``MergeError: conflicting values`` when DataArrays are combined into a
    single :class:`xarray.Dataset`.

    Dropping these non-dimension coordinates is safe because the information
    is already captured in the variable names and metadata.
    """
    drop = [c for c in da.coords if c not in da.dims]
    return da.drop_vars(drop) if drop else da


def _resolve_var(ds: xarray.Dataset, preferred: str) -> xarray.DataArray:
    """Resolve a variable from a dataset, trying common cfgrib aliases.

    cfgrib may decode COSMO GRIB variable names differently depending on
    the eccodes version and GRIB edition.  This helper tries the caller's
    preferred name, then falls back to the first data variable.

    Parameters
    ----------
    ds : xarray.Dataset
    preferred : str
        Preferred variable name.

    Returns
    -------
    xarray.DataArray

    Raises
    ------
    KeyError
        If the dataset has no data variables.
    """
    if preferred in ds:
        return ds[preferred]

    # Try lowercase, common cfgrib short_names
    lower = preferred.lower()
    for name in ds.data_vars:
        if str(name).lower() == lower:
            return ds[name]

    # Last resort: first data variable
    data_vars = list(ds.data_vars)
    if data_vars:
        logger.warning(
            "Variable '%s' not found; falling back to '%s'",
            preferred, data_vars[0],
        )
        return ds[data_vars[0]]

    raise KeyError(f"No data variables in dataset; expected '{preferred}'")


# ---------------------------------------------------------------------------
# Full annual dataset assembly
# ---------------------------------------------------------------------------

def build_annual_dataset(
    year: int | None = None,
    months: list[int] | None = None,
    *,
    grb_dir: Path | None = None,
    include_wind_components: bool = True,
) -> xarray.Dataset:
    """Assemble a complete annual dataset with all derived variables.

    Reads all five raw attributes, applies unit conversions, computes
    GHI/DHI/WS_10M/T, and merges into a single :class:`xarray.Dataset`.

    Parameters
    ----------
    year : int, optional
        Target year (default from config).
    months : list[int], optional
        Months to include (default from config).
    grb_dir : Path, optional
        Root decompressed-GRIB directory.
    include_wind_components : bool
        If ``True`` (default), keep raw ``U_10M`` and ``V_10M`` in the output
        alongside the scalar ``WS_10M``.  A metadata warning is attached noting
        that U/V are in rotated-pole coordinates.

    Returns
    -------
    xarray.Dataset
        Variables: ``T``, ``GHI``, ``DHI``, ``WS_10M``, and optionally
        ``U_10M``, ``V_10M``.  Coordinates include the native rotated-pole
        grid (``rlat``, ``rlon``) and auxiliary WGS84 ``latitude`` /
        ``longitude`` (if the COSMO_REA6_CONST file has been downloaded).

    Notes
    -----
    DNI is intentionally not computed here.  The ``model_buem.py`` thermal
    model derives it per-building via pvlib DISC decomposition from GHI,
    which avoids the ``cos(zenith) → 0`` singularity.
    """
    xr = _import_xarray()
    from .config import get_config

    cfg = get_config()
    year = year or cfg["year"]
    months = months or cfg["months"]

    # ── Initialise dask for parallel compute ────────────────────────
    ncores = cfg["ncores"]
    # Use the threaded scheduler — all threads share the same process
    # memory (28 GiB on a 1/8 Rome node) instead of splitting it across
    # separate worker processes where each gets only 7 GiB.
    # NumPy and cfgrib both release the GIL, so threads are effective.
    import dask
    dask.config.set(scheduler="threads", num_workers=ncores)
    logger.info("Dask threaded scheduler: %d threads", ncores)

    logger.info("Building annual dataset for %d, months=%s", year, months)

    # Load all 5 raw attributes in parallel — cfgrib I/O is the slowest
    # part, and each attribute reads independent files on disk.
    attrs_to_load = ["SWDIFDS_RAD", "SWDIRS_RAD", "T_2M", "U_10M", "V_10M"]

    def _load(attr: str) -> xarray.Dataset:
        return open_grib_year(attr, year, months, grb_dir=grb_dir)

    logger.info("Reading %d attributes in parallel (%d threads)...",
                len(attrs_to_load), min(len(attrs_to_load), ncores))
    with ThreadPoolExecutor(max_workers=min(len(attrs_to_load), ncores)) as pool:
        results = list(pool.map(_load, attrs_to_load))

    ds_diffuse, ds_direct, ds_temp, ds_u, ds_v = results

    # Derive fields
    T = convert_temperature(ds_temp)
    GHI = compute_ghi(ds_diffuse, ds_direct)
    DHI = compute_dhi(ds_diffuse)
    WS = compute_wind_speed(ds_u, ds_v)

    # Strip conflicting non-dimension scalar coordinates (e.g.
    # heightAboveGround, step, surface) before merging — cfgrib attaches
    # different values for different GRIB sources which causes MergeError.
    T = _strip_scalar_coords(T)
    GHI = _strip_scalar_coords(GHI)
    DHI = _strip_scalar_coords(DHI)
    WS = _strip_scalar_coords(WS)

    # Assemble output dataset
    out = xr.Dataset(
        {
            "T": T,
            "GHI": GHI,
            "DHI": DHI,
            "WS_10M": WS,
        },
        attrs={
            "title": f"COSMO-REA6 processed weather data — {year}",
            "source": "DWD COSMO-REA6 reanalysis (https://opendata.dwd.de/climate_environment/REA/COSMO_REA6/)",
            "spatial_resolution": "0.055° (~6 km)",
            "temporal_resolution": "1 hour",
            "processing": "buem.weather pipeline",
            "conventions": "CF-1.8",
            "note_DNI": (
                "DNI is not included in this file.  It must be computed per-site "
                "using pvlib DISC decomposition from GHI to avoid cos(zenith)→0 "
                "divergence.  See buem.weather.from_csv.CsvWeatherData.reconstruct_dni_from_ghi()."
            ),
        },
    )

    if include_wind_components:
        u_raw = _strip_scalar_coords(_resolve_var(ds_u, "u10"))
        v_raw = _strip_scalar_coords(_resolve_var(ds_v, "v10"))
        u_raw.attrs["long_name"] = "U-component of wind at 10m (rotated-pole grid north)"
        u_raw.attrs["warning"] = (
            "This field uses COSMO-REA6 rotated-pole grid coordinates.  "
            "For true-north wind direction, apply the rotated-pole → WGS84 "
            "vector rotation using pyproj or the COSMO rotation angle."
        )
        v_raw.attrs["long_name"] = "V-component of wind at 10m (rotated-pole grid north)"
        v_raw.attrs["warning"] = u_raw.attrs["warning"]
        out["U_10M"] = u_raw
        out["V_10M"] = v_raw

    logger.info(
        "Annual dataset assembled: %d variables, %d timesteps",
        len(out.data_vars), out.sizes.get("time", 0),
    )
    return out
