"""BUEM Weather — COSMO-REA6 data processing pipeline.

This package provides a complete workflow for acquiring and preparing
weather data from the DWD COSMO-REA6 reanalysis for use in the BUEM
building energy model.

Modules
-------
config
    Pipeline configuration, attribute definitions, URL/path helpers.
download
    HTTP/FTP download of compressed GRIB files from DWD OpenData.
decompress
    Parallel bz2 decompression (pbzip2/lbzip2/Python fallback).
transform
    GRIB → xarray conversion, unit normalisation, derived fields.
export
    NetCDF-4 export with zlib compression.
pipeline
    End-to-end orchestrator (download → decompress → transform → export).
from_csv
    Load pre-extracted single-point weather CSV files (existing module).

Quick start
-----------
From the CLI::

    buem weather validate            # check tools are available
    buem weather info                # show resolved configuration
    buem weather run --months 1      # single-month test run
    buem weather run                 # full year (12 months)

From Python::

    from buem.weather.pipeline import run_pipeline
    nc_path = run_pipeline(year=2018, months=[1])
"""
