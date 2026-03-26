# Version: single source of truth is the git tag.
# setuptools-scm writes _version.py at build/install time.
# Fallback chain: _version.py → importlib.metadata → pyproject.toml fallback_version.
try:
    from buem._version import version as __version__
except ImportError:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError
    try:
        __version__ = _pkg_version("buem")
    except PackageNotFoundError:
        __version__ = "0.1.2"  # keep in sync with pyproject.toml fallback_version
