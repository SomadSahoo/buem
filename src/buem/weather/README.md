# BUEM Weather Module — COSMO-REA6 Processing Pipeline

## Overview

This module provides a complete pipeline for downloading, decompressing,
transforming, and exporting COSMO-REA6 reanalysis weather data from the
[DWD OpenData server](https://opendata.dwd.de/climate_environment/REA/COSMO_REA6/)
into analysis-ready NetCDF files for the BUEM thermal model.

```text
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
│  1. DOWNLOAD │───▶│ 2. DECOMPRESS│───▶│ 3. TRANSFORM│───▶│ 4. EXPORT  │
│  .grb.bz2   │    │  .grb        │    │  xarray DS  │    │  .nc       │
│  (DWD HTTPS) │    │  (pbzip2)    │    │  (cfgrib)   │    │  (NetCDF4) │
└─────────────┘    └──────────────┘    └─────────────┘    └────────────┘
```

### Data Source

**COSMO-REA6** is a high-resolution regional reanalysis covering Europe at
~6 km spatial resolution and 1-hour temporal resolution, produced by DWD
(German Weather Service). Data is available from 1995–2019.

### Attributes Processed

| COSMO Field   | Description                           | Raw Unit | Target Unit | Notes              |
|---------------|---------------------------------------|----------|-------------|--------------------|
| `SWDIFDS_RAD` | Diffuse shortwave radiation (surface) | W/m²     | W/m²        | = DHI              |
| `SWDIRS_RAD`  | Direct shortwave radiation (surface)  | W/m²     | W/m²        | Part of GHI        |
| `T_2M`        | Temperature at 2m                     | K        | °C          | `T_2M - 273.15`  |
| `U_10M`       | U-component wind at 10m               | m/s      | m/s         | Rotated-pole coords|
| `V_10M`       | V-component wind at 10m               | m/s      | m/s         | Rotated-pole coords|

### Derived Fields

| Field    | Formula                    | Unit | Notes                                    |
|----------|----------------------------|------|------------------------------------------|
| `GHI`    | `SWDIFDS_RAD + SWDIRS_RAD` | W/m² | Global Horizontal Irradiance             |
| `DHI`    | `SWDIFDS_RAD`              | W/m² | Diffuse Horizontal Irradiance            |
| `T`      | `T_2M - 273.15`            | °C   | Temperature in Celsius                   |
| `WS_10M` | `sqrt(U_10M² + V_10M²)`   | m/s  | Scalar wind speed (coordinate-invariant) |

> **DNI is intentionally NOT computed on the server grid.**
> `DNI = SWDIRS_RAD / cos(θ_z)` diverges when the sun is near the horizon
> (`cos(θ_z) → 0`). The thermal model (`model_buem.py`) derives DNI per-building
> using pvlib's DISC decomposition from GHI, which is numerically stable.

---

## Quick Start

### 1. Server Environment Setup (Standalone — no full buem install)

The weather module runs **standalone** on a server. You do NOT need the full
buem package (no cvxpy, flask, etc.) or `pip install -e .`.

**Option A: Clone the full repo** (simplest — PYTHONPATH set automatically by the SLURM scripts):

```bash
git clone <repo_url> buem
cd buem
```

**Option B: Copy only the weather package** to the server:

```bash
scp -r src/buem/weather/ user@server:~/weather/buem/weather/
```

Then create the lightweight conda environment:

```bash
# From the repo root (uses weather_env.yml):
bash src/buem/weather/shell_scripts/setup_env.sh weather_env

# Or directly from the yml:
conda env create -f src/buem/weather/weather_env.yml

conda activate weather_env
```

### 2. Configuration

Copy `.env.example` to `.env` and fill in server-specific values:

```bash
cp .env.example .env
```

Key variables for the weather pipeline:

```ini
# Working directory for all pipeline data
COSMO_WORK_DIR=$HOME/buem_weather

# Year to process
COSMO_YEAR=2018

# Months (comma-separated; use "01" for a single-month test)
COSMO_MONTHS=01,02,03,04,05,06,07,08,09,10,11,12

# CPU cores for parallel decompression
COSMO_NCORES=16

# Threads per decompression job
COSMO_THREADS_PER_JOB=4

# SLURM settings
COSMO_SLURM_PARTITION=rome
COSMO_SLURM_EMAIL=your.email@example.com
```

### 3. Validate Environment

```bash
python -m buem.weather validate    # check all tools are available
python -m buem.weather info        # show resolved configuration
```

### 4. Run the Pipeline

**Single-month test run (recommended first):**

```bash
python -m buem.weather run --months 1
```

**Full year:**

```bash
python -m buem.weather run
```

**Via SLURM on Snellius (SURF):**

```bash
# Set PYTHONPATH if you cloned the full repo:
export PYTHONPATH=/path/to/buem/src:$PYTHONPATH

# Single-month test (rome partition, 1/8 node = 16 cores, ~16 SBU/h)
sbatch src/buem/weather/shell_scripts/run_pipeline.sh --months 1

# Full year
sbatch src/buem/weather/shell_scripts/run_pipeline.sh

# Download-only (staging partition — designed for data transfers)
sbatch src/buem/weather/shell_scripts/download.sh

# Streaming download + decompress
sbatch src/buem/weather/shell_scripts/decompress.sh
```

### 5. Step-by-step Execution

You can also run individual steps:

```bash
# Download only (via SLURM on staging partition)
sbatch src/buem/weather/shell_scripts/download.sh

# Then run transform+export (skip download and decompress)
python -m buem.weather run --skip-download --skip-decompress
```

---

## Directory Structure

After running the pipeline, the working directory looks like:

```text
$COSMO_WORK_DIR/
├── download/              # Raw .grb.bz2 files from DWD
│   ├── SWDIFDS_RAD/
│   │   ├── SWDIFDS_RAD.2D.201801.grb.bz2
│   │   ├── ...
│   │   └── SWDIFDS_RAD.2D.201812.grb.bz2
│   ├── SWDIRS_RAD/
│   ├── T_2M/
│   ├── U_10M/
│   └── V_10M/
├── decompress/            # Decompressed .grb files
│   ├── SWDIFDS_RAD/
│   │   ├── SWDIFDS_RAD.2D.201801.grb
│   │   └── ...
│   └── ...
└── output/                # Final NetCDF file
    └── COSMO_REA6_2018.nc
```

---

## Architecture

### Module Overview

```text
src/buem/weather/
├── __init__.py          # Package docstring and public API summary
├── __main__.py          # Standalone CLI: python -m buem.weather
├── config.py            # Configuration: URLs, attributes, paths, .env loading
├── download.py          # HTTPS/FTP download with integrity checks
├── decompress.py        # Parallel bz2 decompression (pbzip2/lbzip2/Python)
├── transform.py         # GRIB→xarray, unit conversion, derived fields
├── export.py            # NetCDF-4 export with zlib compression
├── pipeline.py          # End-to-end orchestrator
├── from_csv.py          # Existing: load single-point CSV weather data
├── weather_env.yml      # Standalone conda environment (weather-only deps)
└── shell_scripts/
    ├── setup_env.sh     # Conda environment creation (uses weather_env.yml)
    ├── run_pipeline.sh  # SLURM full pipeline (rome partition)
    ├── download.sh      # SLURM download-only (staging partition)
    ├── decompress.sh    # SLURM streaming download + decompress (rome)
    └── grb.sh           # SLURM decompress-only (rome)
```

### Design Decisions

1. **Idempotent steps**: Every step checks for existing output before
   processing. Re-running is safe and skips completed work.

2. **Atomic writes**: Downloads and decompressions write to a `.part`
   temporary file, then atomically rename. A crash never leaves a
   corrupt file that would be mistaken for a completed one.

3. **Server-client split**: Heavy processing (GRIB reading, xarray
   operations) runs on the Linux HPC server. The thermal model on
   Windows reads the final CSV or NetCDF output.

4. **DNI deferred**: DNI computation is left to the thermal model
   (`model_buem.py`) which already uses pvlib DISC decomposition. This
   avoids the `cos(zenith)→0` singularity and is per-building accurate.

5. **Wind components kept**: Raw `U_10M` and `V_10M` are preserved in
   the NetCDF for power users who need wind direction. A metadata
   warning notes they are in rotated-pole coordinates. The scalar
   `WS_10M` (wind speed magnitude) is coordinate-invariant and ready
   for immediate use.

6. **Conda-only dependencies**: All packages are installable from
   `conda-forge`. No `pip install -e .` required.

7. **Standalone operation**: The weather package uses **relative imports**
   and loads `.env` via `python-dotenv` directly. It does not depend on
   the `buem` parent package. Run it with `python -m buem.weather`
   after setting `PYTHONPATH` to include the `src/` directory.

### Unit Compatibility with `model_buem.py`

The thermal model expects weather data in a pandas DataFrame with columns:

- `T` — temperature in **°C**
- `GHI` — global horizontal irradiance in **W/m²**
- `DHI` — diffuse horizontal irradiance in **W/m²**
- `DNI` — direct normal irradiance in **W/m²** (reconstructed from GHI by pvlib DISC)

The pipeline output matches these conventions. The `from_csv.py` module
loads single-point data from CSV and optionally reconstructs DNI via DISC.

### Coordinate System Notes

COSMO-REA6 uses a **rotated pole** coordinate system:

- Grid coordinates: `rlat`, `rlon` (rotated latitude/longitude)
- The `U_10M` and `V_10M` wind components are aligned to the **rotated grid north**,
  not geographic (WGS84) north.

**Scalar quantities** (temperature, radiation, wind speed magnitude) are
identical in both coordinate systems — no rotation needed.

**Vector wind direction** (if needed for facade-specific analysis): users
must rotate `(U_10M, V_10M)` from rotated-pole to WGS84 using `pyproj`
or the COSMO rotation angle. This is documented in the NetCDF metadata.

---

## Dependencies

All installed via `conda install conda-forge::<package>`:

| Package        | Purpose                                 |
|----------------|-----------------------------------------|
| `cfgrib`       | GRIB file engine for xarray             |
| `eccodes`      | ECMWF GRIB/BUFR codec (cfgrib backend)  |
| `netcdf4`      | NetCDF-4 file I/O                       |
| `pyproj`       | Coordinate transformations (optional)   |
| `pvlib`        | Solar position and DNI computation      |
| `xarray`       | N-dimensional labelled arrays           |
| `pandas`       | Time series handling                    |
| `numpy`        | Numerical operations                    |
| `python-dotenv`| `.env` file loading                     |

Server tools (available in `$PATH`):

- `pbzip2` or `lbzip2` — parallel bzip2 (recommended; Python `bz2` fallback ok)
- `curl` or `wget` — HTTP download

---

## Troubleshooting

### "cfgrib engine not found"

```bash
conda install conda-forge::cfgrib conda-forge::eccodes
```

### Slow decompression

Install a parallel decompressor:

```bash
conda install conda-forge::pbzip2
# or use lbzip2 if available on your server
```

### Download fails / timeouts

- Check network access to `opendata.dwd.de`.
- Re-run: the pipeline skips already-downloaded files.
- For firewalled servers, download via the shell script on a login node
  with internet access, then run `python -m buem.weather run --skip-download`.

### "Variable 'SWDIFDS_RAD' not found"

cfgrib decodes COSMO variable names differently across eccodes versions.
The `transform.py` module tries multiple name variants. If it still fails,
inspect the GRIB with:

```bash
grib_ls path/to/file.grb | head -20
```

And report the variable name — we'll add it to the alias list.

---

## Snellius (SURF) Deployment

### Partition Guide

| Partition | Cores | Memory  | Min allocation     | SBU weight | Use for              |
|-----------|-------|---------|--------------------|------------|----------------------|
| `rome`    | 128   | 224 GiB | 1/8 node (16 cores, 28 GiB) | 1.0 | Decompress + transform |
| `genoa`   | 192   | 336 GiB | 1/8 node (24 cores, 42 GiB) | 1.0 | Large transforms     |
| `staging` | 16    | 224 GiB | full node          | 2.0        | Data transfer (download) |

**Max wall time**: 120 hours (5 days).  No `sudo` — use conda for packages.

### Recommended Workflow

```bash
# 1. Set up environment (one-time)
bash src/buem/weather/shell_scripts/setup_env.sh weather_env

# 2. Configure .env
cp .env.example .env
# Edit .env: set COSMO_WORK_DIR, COSMO_YEAR, etc.

# 3. Download data (staging partition — meant for data transfers)
sbatch src/buem/weather/shell_scripts/download.sh

# 4. After download completes, run decompress + transform + export
sbatch src/buem/weather/shell_scripts/run_pipeline.sh --skip-download

# Or do everything in one job (downloads on compute node):
sbatch src/buem/weather/shell_scripts/run_pipeline.sh
```

### SBU Budget Estimate

- **Download only** (staging, ~2h): 2 × 16 cores × 1.0 = **32 SBU**
- **Full pipeline** (rome, 1/8 node, ~4h): 4 × 16 × 1.0 = **64 SBU**
- **Transform only** (rome, 1/8 node, ~1h): 1 × 16 × 1.0 = **16 SBU**
