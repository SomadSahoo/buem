from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("buem")
except PackageNotFoundError:
    __version__ = "0.0.0"
