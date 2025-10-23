"""Modular Caesar cipher package with GUI and CLI helpers."""

from importlib import metadata

from .app import run
from .core import LOWER, UPPER, caesar, decode, encode, mapping_pairs

try:
    __version__ = metadata.version("caesar-cli")
except metadata.PackageNotFoundError:  # pragma: no cover - local dev
    __version__ = "0.0.0"


def cli_main(argv=None):
    from .cli import main as _main

    return _main(argv)

__all__ = [
    "run",
    "cli_main",
    "caesar",
    "encode",
    "decode",
    "mapping_pairs",
    "LOWER",
    "UPPER",
    "__version__",
]
