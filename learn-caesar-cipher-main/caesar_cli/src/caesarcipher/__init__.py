"""Core Caesar-cipher utilities and CLI helpers."""

from importlib import metadata

from .core import LOWER_ALPHABET, UPPER_ALPHABET, caesar, decode, encode, mapping_pairs

try:
    __version__ = metadata.version("caesar-cli")
except metadata.PackageNotFoundError:  # pragma: no cover - during local dev
    __version__ = "0.0.0"

__all__ = [
    "caesar",
    "encode",
    "decode",
    "mapping_pairs",
    "LOWER_ALPHABET",
    "UPPER_ALPHABET",
    "__version__",
]
