"""Core Caesar cipher utilities."""

from __future__ import annotations

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = LOWER.upper()
_ALPHABET_SIZE = len(LOWER)


def caesar(text: str, shift: int, *, encode: bool = True) -> str:
    """Encode or decode ``text`` using a Caesar shift.

    Args:
        text: Input string to transform.
        shift: Amount to rotate the alphabet (`1`-`25` inclusive).
        encode: Set ``False`` to perform decoding.

    Returns:
        Transformed string.

    Raises:
        ValueError: If ``shift`` is outside the valid range.
        TypeError: If ``shift`` is not an ``int``.
    """

    normalised = _normalise_shift(shift)
    if not encode:
        normalised = (-normalised) % _ALPHABET_SIZE

    shifted_lower = LOWER[normalised:] + LOWER[:normalised]
    shifted_upper = UPPER[normalised:] + UPPER[:normalised]
    table = str.maketrans(LOWER + UPPER, shifted_lower + shifted_upper)
    return text.translate(table)


def encode(text: str, shift: int) -> str:
    """Encode ``text`` using a positive shift."""

    return caesar(text, shift, encode=True)


def decode(text: str, shift: int) -> str:
    """Decode ``text`` that was previously Caesar encoded with ``shift``."""

    return caesar(text, shift, encode=False)


def mapping_pairs(shift: int, *, encode: bool = True) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (lowercase, uppercase) mapping pairs for the given shift."""

    normalised = _normalise_shift(shift)
    src_lower = LOWER
    dst_lower = LOWER[normalised:] + LOWER[:normalised]
    src_upper = UPPER
    dst_upper = UPPER[normalised:] + UPPER[:normalised]

    if not encode:
        src_lower, dst_lower = dst_lower, src_lower
        src_upper, dst_upper = dst_upper, src_upper

    return list(zip(src_lower, dst_lower)), list(zip(src_upper, dst_upper))


def _normalise_shift(shift: int) -> int:
    if not isinstance(shift, int):
        raise TypeError("shift must be an int between 1 and 25")
    if not 1 <= shift <= 25:
        raise ValueError("shift must be between 1 and 25")
    return shift % _ALPHABET_SIZE


__all__ = ["caesar", "encode", "decode", "mapping_pairs", "LOWER", "UPPER"]
