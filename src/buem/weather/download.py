"""Download COSMO-REA6 GRIB files from the DWD OpenData server.

Supports two transports:

* **HTTPS** (default) — uses ``urllib.request`` from the standard library;
  no extra dependencies.  Resume via ``Range`` header is attempted when the
  server supports it.
* **FTP** — available as a fallback via :func:`download_ftp`.  Uses
  :mod:`ftplib` (stdlib).

Both paths perform an **integrity check** by comparing the local file size
to the remote ``Content-Length`` (HTTPS) or ``SIZE`` (FTP) *before*
downloading, so an already-complete file is never re-fetched.

Typical usage::

    from buem.weather.download import download_attribute_month
    download_attribute_month("SWDIRS_RAD", 2018, 1, dest_dir=Path("/data"))
"""

from __future__ import annotations

import ftplib
import logging
import shutil
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import ATTRIBUTES, grib_filename, grib_url, get_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _remote_size_https(url: str) -> int | None:
    """Return the remote file size via an HTTP HEAD request, or *None*."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else None
    except (urllib.error.URLError, ValueError, OSError) as exc:
        logger.debug("HEAD request failed for %s: %s", url, exc)
        return None


def _download_https(url: str, dest: Path) -> Path:
    """Download *url* to *dest* via HTTPS with atomic write.

    If *dest* already exists and its size matches the remote
    ``Content-Length``, the download is skipped.

    Parameters
    ----------
    url : str
        Full URL to the file.
    dest : Path
        Local destination path.

    Returns
    -------
    Path
        The (possibly already existing) local file path.

    Raises
    ------
    RuntimeError
        If the download fails or produces a zero-byte file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    remote_size = _remote_size_https(url)
    if dest.exists():
        local_size = dest.stat().st_size
        if remote_size and local_size == remote_size:
            logger.info("Already downloaded (size OK): %s", dest.name)
            return dest
        if remote_size:
            logger.warning(
                "Local size %d != remote %d for %s — re-downloading",
                local_size, remote_size, dest.name,
            )

    logger.info("Downloading %s → %s", url, dest.name)

    # Write to a temp file first, then atomically rename to avoid partial files.
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=dest.parent, prefix=f".{dest.name}.", suffix=".part"
    )
    try:
        with open(tmp_fd, "wb") as tmp_f:
            with urllib.request.urlopen(url, timeout=600) as resp:
                shutil.copyfileobj(resp, tmp_f, length=1 << 20)  # 1 MiB chunks
        # Verify size
        actual = Path(tmp_path).stat().st_size
        if actual == 0:
            raise RuntimeError(f"Downloaded file is empty: {url}")
        if remote_size and actual != remote_size:
            raise RuntimeError(
                f"Size mismatch: expected {remote_size}, got {actual} for {url}"
            )
        Path(tmp_path).replace(dest)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    logger.info("Download complete: %s (%d bytes)", dest.name, dest.stat().st_size)
    return dest


# ---------------------------------------------------------------------------
# FTP transport (fallback)
# ---------------------------------------------------------------------------

def download_ftp(
    host: str,
    remote_path: str,
    dest: Path,
    *,
    user: str = "anonymous",
    passwd: str = "",
) -> Path:
    """Download a single file from an FTP server.

    Parameters
    ----------
    host : str
        FTP hostname (e.g. ``"opendata.dwd.de"``).
    remote_path : str
        Full path on the FTP server.
    dest : Path
        Local destination path.
    user, passwd : str
        FTP credentials.  DWD OpenData allows anonymous access.

    Returns
    -------
    Path
        Local file path.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    with ftplib.FTP(host, timeout=120) as ftp:
        ftp.login(user=user, passwd=passwd)
        remote_size: int | None = None
        try:
            remote_size = ftp.size(remote_path)
        except ftplib.error_perm:
            pass

        if dest.exists() and remote_size and dest.stat().st_size == remote_size:
            logger.info("Already downloaded (FTP size OK): %s", dest.name)
            return dest

        logger.info("FTP downloading %s → %s", remote_path, dest.name)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=dest.parent, prefix=f".{dest.name}.", suffix=".part"
        )
        try:
            with open(tmp_fd, "wb") as tmp_f:
                ftp.retrbinary(f"RETR {remote_path}", tmp_f.write, blocksize=1 << 20)
            Path(tmp_path).replace(dest)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    logger.info("FTP download complete: %s", dest.name)
    return dest


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_attribute_month(
    attribute: str,
    year: int,
    month: int,
    *,
    dest_dir: Path | None = None,
    base_url: str | None = None,
) -> Path:
    """Download one monthly GRIB file for a single COSMO-REA6 attribute.

    Parameters
    ----------
    attribute : str
        Attribute name (must be a key in :data:`~buem.weather.config.ATTRIBUTES`).
    year : int
        Four-digit year (e.g. 2018).
    month : int
        Month (1–12).
    dest_dir : Path, optional
        Download directory.  Defaults to ``<work_dir>/download/<attribute>/``.
    base_url : str, optional
        Override the DWD base URL.

    Returns
    -------
    Path
        Path to the local ``.grb.bz2`` file.

    Raises
    ------
    ValueError
        If *attribute* is not a recognised COSMO-REA6 field.
    """
    if attribute not in ATTRIBUTES:
        raise ValueError(
            f"Unknown attribute '{attribute}'.  "
            f"Valid: {', '.join(sorted(ATTRIBUTES))}"
        )

    cfg = get_config()
    if dest_dir is None:
        dest_dir = cfg["download_dir"] / attribute
    dest_dir.mkdir(parents=True, exist_ok=True)

    fname = grib_filename(attribute, year, month)
    url = grib_url(attribute, year, month, base_url=base_url)
    dest = dest_dir / fname

    return _download_https(url, dest)


def download_all(
    year: int | None = None,
    months: list[int] | None = None,
    attributes: list[str] | None = None,
    *,
    dest_dir: Path | None = None,
    base_url: str | None = None,
) -> list[Path]:
    """Download all requested GRIB files for a given year.

    Parameters
    ----------
    year : int, optional
        Year to download (default from config: 2018).
    months : list[int], optional
        Months to download (default from config: 1–12).
    attributes : list[str], optional
        Attributes to download (default from config: all five).
    dest_dir : Path, optional
        Root download directory.  Per-attribute sub-directories are created.
    base_url : str, optional
        Override DWD base URL.

    Returns
    -------
    list[Path]
        Paths to all downloaded ``.grb.bz2`` files.
    """
    cfg = get_config()
    year = year or cfg["year"]
    months = months or cfg["months"]
    attributes = attributes or cfg["attributes"]

    # Build list of (attribute, month) jobs
    jobs = [
        (attr, m) for attr in attributes for m in months
    ]

    def _download_one(args: tuple[str, int]) -> Path:
        attr, m = args
        return download_attribute_month(
            attr, year, m, dest_dir=dest_dir, base_url=base_url
        )

    # Download in parallel — each file goes to a separate server path,
    # so concurrent connections are safe and ≈N× faster.
    max_workers = min(len(jobs), cfg["ncores"], 8)  # cap at 8 to be polite to DWD
    logger.info(
        "Downloading %d files with %d parallel workers", len(jobs), max_workers
    )

    downloaded: list[Path] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_download_one, j): j for j in jobs}
        for future in as_completed(futures):
            attr, m = futures[future]
            try:
                p = future.result()
                downloaded.append(p)
            except Exception:
                logger.exception("Failed to download %s month %d", attr, m)
                raise

    logger.info("Downloaded %d files.", len(downloaded))
    return downloaded
