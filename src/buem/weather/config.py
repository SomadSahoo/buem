"""Weather pipeline configuration for COSMO-REA6 data processing.

Centralises all configurable parameters — URLs, paths, attribute definitions,
unit conversion factors — so that every other module in the weather package
imports from here rather than hard-coding values.

Configuration is resolved in the following priority order:
    1. Environment variables (``COSMO_*``) — highest priority.
    2. ``.env`` file loaded by :mod:`buem.env`.
    3. Defaults defined in this module.

Typical usage::

    from buem.weather.config import get_config
    cfg = get_config()          # dict with all resolved settings
    print(cfg["work_dir"])      # e.g. /home/user/buem_weather
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Load .env file if python-dotenv is available.
# This makes the weather package self-contained — it does NOT depend on
# buem.env.load_env() and can run standalone on a server.
try:
    from dotenv import load_dotenv as _load_dotenv

    # Walk up from this file to find .env (works both inside buem repo and
    # when the weather package is copied standalone to a server).
    _env_candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",  # src/buem/weather → repo root
    ]
    for _p in _env_candidates:
        if _p.is_file():
            _load_dotenv(_p, override=False)
            break
except ImportError:
    pass  # python-dotenv not installed — rely on OS environment


# ---------------------------------------------------------------------------
# COSMO-REA6 attribute / parameter definitions
# ---------------------------------------------------------------------------
# Each entry maps a short name used in file paths to metadata required for
# downloading, interpreting, and converting the GRIB field.
#
# Keys:
#   dwd_name     – directory name on the DWD OpenData server
#   description  – human-readable description
#   unit_raw     – unit in the raw GRIB file
#   unit_target  – unit after our conversion (matches model_buem.py expectations)
#   conversion   – symbolic note on what transform is applied (actual code in transform.py)

ATTRIBUTES: dict[str, dict[str, str]] = {
    "SWDIFDS_RAD": {
        "dwd_name": "SWDIFDS_RAD",
        "description": "Downward diffuse shortwave radiation at surface (instantaneous)",
        "unit_raw": "W/m2",
        "unit_target": "W/m2",
        "conversion": "none (already instantaneous W/m2)",
    },
    "SWDIRS_RAD": {
        "dwd_name": "SWDIRS_RAD",
        "description": "Downward direct shortwave radiation at surface (instantaneous)",
        "unit_raw": "W/m2",
        "unit_target": "W/m2",
        "conversion": "none (already instantaneous W/m2)",
    },
    "T_2M": {
        "dwd_name": "T_2M",
        "description": "Temperature at 2 m above ground",
        "unit_raw": "K",
        "unit_target": "degC",
        "conversion": "T_2M - 273.15",
    },
    "U_10M": {
        "dwd_name": "U_10M",
        "description": "U-component of wind at 10 m (rotated-pole grid north)",
        "unit_raw": "m/s",
        "unit_target": "m/s",
        "conversion": "kept as-is in rotated-pole coordinates",
    },
    "V_10M": {
        "dwd_name": "V_10M",
        "description": "V-component of wind at 10 m (rotated-pole grid north)",
        "unit_raw": "m/s",
        "unit_target": "m/s",
        "conversion": "kept as-is in rotated-pole coordinates",
    },
}

# Derived fields computed during the transform step
DERIVED_FIELDS: dict[str, dict[str, str]] = {
    "GHI": {
        "description": "Global Horizontal Irradiance = SWDIFDS_RAD + SWDIRS_RAD",
        "unit": "W/m2",
    },
    "DHI": {
        "description": "Diffuse Horizontal Irradiance = SWDIFDS_RAD",
        "unit": "W/m2",
    },
    "WS_10M": {
        "description": "Wind speed at 10 m = sqrt(U_10M^2 + V_10M^2)",
        "unit": "m/s",
    },
    "T": {
        "description": "Temperature at 2 m (Celsius) = T_2M - 273.15",
        "unit": "degC",
    },
}


# ---------------------------------------------------------------------------
# File naming conventions
# ---------------------------------------------------------------------------
# Raw GRIB files on DWD follow the pattern:
#   {ATTR}.2D.{YYYYMM}.grb.bz2
# e.g. SWDIRS_RAD.2D.201801.grb.bz2

def grib_filename(attribute: str, year: int, month: int) -> str:
    """Return the standard GRIB filename for a given attribute/year/month.

    Parameters
    ----------
    attribute : str
        COSMO-REA6 attribute name (e.g. ``"SWDIRS_RAD"``).
    year : int
        Four-digit year.
    month : int
        Month number (1–12).

    Returns
    -------
    str
        Filename like ``SWDIRS_RAD.2D.201801.grb.bz2``.
    """
    return f"{attribute}.2D.{year}{month:02d}.grb.bz2"


def grib_url(attribute: str, year: int, month: int, base_url: str | None = None) -> str:
    """Return the full download URL for a COSMO-REA6 GRIB file.

    Parameters
    ----------
    attribute : str
        COSMO-REA6 attribute name.
    year, month : int
        Target period.
    base_url : str, optional
        Override the DWD base URL (useful for mirrors or local servers).

    Returns
    -------
    str
        Full URL to the ``.grb.bz2`` file.
    """
    base = base_url or os.environ.get(
        "COSMO_BASE_URL",
        "https://opendata.dwd.de/climate_environment/REA/COSMO_REA6/hourly/2D",
    )
    fname = grib_filename(attribute, year, month)
    return f"{base}/{attribute}/{fname}"


# ---------------------------------------------------------------------------
# Resolved pipeline configuration
# ---------------------------------------------------------------------------

def get_config() -> dict[str, Any]:
    """Return the fully-resolved pipeline configuration dictionary.

    All values come from environment variables (``COSMO_*``) with sensible
    defaults.  Path values are resolved to absolute :class:`pathlib.Path`
    objects.

    Returns
    -------
    dict[str, Any]
        Keys include ``base_url``, ``const_url``, ``work_dir``, ``year``,
        ``months``, ``attributes``, ``ncores``, ``threads_per_job``,
        ``decompressor``, ``conda_env``, ``slurm_partition``, ``slurm_email``.
    """
    work_dir = Path(
        os.environ.get("COSMO_WORK_DIR", str(Path.home() / "buem_weather"))
    ).expanduser().resolve()

    months_str = os.environ.get(
        "COSMO_MONTHS", "01,02,03,04,05,06,07,08,09,10,11,12"
    )
    months = [int(m.strip()) for m in months_str.split(",") if m.strip()]

    return {
        "base_url": os.environ.get(
            "COSMO_BASE_URL",
            "https://opendata.dwd.de/climate_environment/REA/COSMO_REA6/hourly/2D",
        ),
        "const_url": os.environ.get(
            "COSMO_CONST_URL",
            "https://opendata.dwd.de/climate_environment/REA/COSMO_REA6/constant",
        ),
        "work_dir": work_dir,
        "download_dir": work_dir / "download",
        "decompress_dir": work_dir / "decompress",
        "processed_dir": work_dir / "processed",
        "output_dir": work_dir / "output",
        "year": int(os.environ.get("COSMO_YEAR", "2018")),
        "months": months,
        "attributes": list(ATTRIBUTES.keys()),
        "ncores": int(os.environ.get(
            "COSMO_NCORES",
            os.environ.get("SLURM_CPUS_PER_TASK", str(os.cpu_count() or 4)),
        )),
        "threads_per_job": int(os.environ.get("COSMO_THREADS_PER_JOB", "4")),
        "decompressor": os.environ.get("COSMO_DECOMPRESSOR", ""),
        "conda_env": os.environ.get("COSMO_CONDA_ENV", "buem_env"),
        "slurm_partition": os.environ.get("COSMO_SLURM_PARTITION", "rome"),
        "slurm_email": os.environ.get("COSMO_SLURM_EMAIL", ""),
    }
