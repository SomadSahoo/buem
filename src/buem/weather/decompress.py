"""Decompress COSMO-REA6 ``.grb.bz2`` files to raw GRIB.

Three strategies are supported — chosen automatically or via the
``COSMO_DECOMPRESSOR`` environment variable:

1. **pbzip2** — parallel BZIP2 (fastest on multi-core servers).
2. **lbzip2** — alternative parallel BZIP2.
3. **Python bz2** — stdlib fallback; no external tools needed.

The decompressor writes to a temporary file and atomically renames it to
the target name, so a crash never leaves a half-written GRIB file.

Typical usage::

    from buem.weather.decompress import decompress_file
    grb = decompress_file(Path("SWDIRS_RAD.2D.201801.grb.bz2"))
"""

from __future__ import annotations

import bz2
import logging
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import get_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decompressor detection
# ---------------------------------------------------------------------------

def _detect_decompressor() -> str:
    """Return the best available decompressor command name.

    Checks ``COSMO_DECOMPRESSOR`` env var first, then probes the ``PATH``
    for ``lbzip2`` and ``pbzip2`` in order.  Falls back to ``"python"``
    which triggers the pure-Python :mod:`bz2` path.

    lbzip2 is preferred over pbzip2 because it scales better with many
    cores and has lower per-thread overhead.

    Returns
    -------
    str
        One of ``"lbzip2"``, ``"pbzip2"``, or ``"python"``.
    """
    cfg = get_config()
    preferred = cfg["decompressor"]
    if preferred:
        if shutil.which(preferred):
            return preferred
        logger.warning(
            "Configured decompressor '%s' not found in PATH; auto-detecting.",
            preferred,
        )

    for cmd in ("lbzip2", "pbzip2"):
        if shutil.which(cmd):
            return cmd

    return "python"


# ---------------------------------------------------------------------------
# Per-strategy decompression
# ---------------------------------------------------------------------------

def _decompress_external(
    src: Path, dest: Path, cmd: str, threads: int
) -> Path:
    """Decompress using an external parallel bzip2 tool.

    Parameters
    ----------
    src : Path
        Input ``.grb.bz2`` file.
    dest : Path
        Output ``.grb`` file.
    cmd : str
        Executable name (``pbzip2`` or ``lbzip2``).
    threads : int
        Number of threads to allocate.

    Returns
    -------
    Path
        The output file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=dest.parent, prefix=f".{dest.name}.", suffix=".part"
    )

    if cmd == "pbzip2":
        args = [cmd, "-d", f"-p{threads}", "-c", str(src)]
    else:  # lbzip2
        args = [cmd, "-d", "-n", str(threads), "-c", str(src)]

    try:
        with open(tmp_fd, "wb") as out_f:
            proc = subprocess.run(
                args,
                stdout=out_f,
                stderr=subprocess.PIPE,
                check=True,
            )
            if proc.stderr:
                logger.debug("Decompressor stderr: %s", proc.stderr.decode(errors="replace"))
        Path(tmp_path).replace(dest)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    return dest


def _decompress_python(src: Path, dest: Path) -> Path:
    """Decompress using Python's :mod:`bz2` (single-threaded fallback).

    Parameters
    ----------
    src : Path
        Input ``.grb.bz2`` file.
    dest : Path
        Output ``.grb`` file.

    Returns
    -------
    Path
        The output file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=dest.parent, prefix=f".{dest.name}.", suffix=".part"
    )

    try:
        with bz2.open(src, "rb") as f_in, open(tmp_fd, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out, length=1 << 20)  # 1 MiB chunks
        Path(tmp_path).replace(dest)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    return dest


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def decompress_file(
    src: Path,
    *,
    dest_dir: Path | None = None,
    threads: int | None = None,
) -> Path:
    """Decompress a single ``.grb.bz2`` file to GRIB.

    If the output already exists and is non-empty, decompression is skipped.

    Parameters
    ----------
    src : Path
        Path to the compressed ``.grb.bz2`` file.
    dest_dir : Path, optional
        Directory for the decompressed output.  Defaults to same directory
        as *src* with ``.bz2`` stripped.
    threads : int, optional
        Threads for pbzip2/lbzip2 (default from config).

    Returns
    -------
    Path
        Path to the decompressed ``.grb`` file.
    """
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")
    if not src.name.endswith(".bz2"):
        raise ValueError(f"Expected a .bz2 file, got: {src.name}")

    grb_name = src.name.removesuffix(".bz2")
    if dest_dir is None:
        dest = src.parent / grb_name
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / grb_name

    # Skip if output already exists and has non-zero size
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("Already decompressed: %s", dest.name)
        return dest

    cfg = get_config()
    threads = threads or cfg["threads_per_job"]
    decompressor = _detect_decompressor()

    logger.info(
        "Decompressing %s with %s (%d threads)",
        src.name, decompressor, threads,
    )

    if decompressor == "python":
        return _decompress_python(src, dest)
    else:
        return _decompress_external(src, dest, decompressor, threads)


def decompress_all(
    src_dir: Path | None = None,
    *,
    dest_dir: Path | None = None,
    attributes: list[str] | None = None,
    year: int | None = None,
    months: list[int] | None = None,
    threads: int | None = None,
) -> list[Path]:
    """Decompress all ``.grb.bz2`` files for the configured attributes/year.

    Parameters
    ----------
    src_dir : Path, optional
        Root directory containing per-attribute sub-dirs with ``.grb.bz2`` files.
        Defaults to ``<work_dir>/download/``.
    dest_dir : Path, optional
        Root directory for decompressed output (per-attribute sub-dirs created).
        Defaults to ``<work_dir>/decompress/``.
    attributes, year, months : optional
        Override the defaults from :func:`~buem.weather.config.get_config`.
    threads : int, optional
        Threads per decompress job.

    Returns
    -------
    list[Path]
        Paths to all decompressed ``.grb`` files.
    """
    from .config import grib_filename

    cfg = get_config()
    src_dir = src_dir or cfg["download_dir"]
    dest_dir = dest_dir or cfg["decompress_dir"]
    attributes = attributes or cfg["attributes"]
    year = year or cfg["year"]
    months = months or cfg["months"]

    jobs: list[tuple[Path, Path]] = []
    for attr in attributes:
        for m in months:
            bz2_name = grib_filename(attr, year, m)
            bz2_path = src_dir / attr / bz2_name
            if not bz2_path.exists():
                logger.warning("Missing compressed file: %s", bz2_path)
                continue
            jobs.append((bz2_path, dest_dir / attr))

    if not jobs:
        logger.warning("No files found to decompress.")
        return []

    # Strategy: decompress multiple files concurrently, dividing total
    # cores across concurrent jobs.  For N files and C total cores:
    #   - parallel_files = min(N, max(2, C // 4))
    #   - threads_per_file = max(1, C // parallel_files)
    # This keeps all cores busy while avoiding I/O contention.
    ncores = cfg["ncores"]
    n_files = len(jobs)
    parallel_files = min(n_files, max(2, ncores // 4))
    threads_per_file = threads or max(1, ncores // parallel_files)

    decompressor = _detect_decompressor()
    logger.info(
        "Decompressing %d files: %d concurrent jobs × %d threads (%s)",
        n_files, parallel_files, threads_per_file, decompressor,
    )

    def _do_decompress(args: tuple[Path, Path]) -> Path:
        bz2_path, out_dir = args
        return decompress_file(
            bz2_path, dest_dir=out_dir, threads=threads_per_file,
        )

    output_paths: list[Path] = []
    with ThreadPoolExecutor(max_workers=parallel_files) as pool:
        futures = {pool.submit(_do_decompress, j): j for j in jobs}
        for future in as_completed(futures):
            bz2_path, _ = futures[future]
            try:
                grb = future.result()
                output_paths.append(grb)
            except Exception:
                logger.exception("Failed to decompress %s", bz2_path)
                raise

    logger.info("Decompressed %d files.", len(output_paths))
    return output_paths
