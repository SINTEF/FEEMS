try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version  # type: ignore

try:
    __version__ = version("MachSysS")
except Exception:
    __version__ = "unknown"
