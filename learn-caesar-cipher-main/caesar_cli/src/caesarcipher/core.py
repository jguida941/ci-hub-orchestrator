"""Pure Caesar cipher helpers used by the CLI and by tutorials."""

from __future__ import annotations

from typing import List, Tuple

LOWER_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
UPPER_ALPHABET = LOWER_ALPHABET.upper()
_ALPHABET_SIZE = len(LOWER_ALPHABET)


def _normalise_shift(shift: int) -> int:
    """Return a positive shift in the range 1-25.

    Args:
        shift: User supplied shift value.

    Raises:
        TypeError: If ``shift`` is not an integer.
        ValueError: If the normalised shift would be 0 (i.e. multiples of 26).
    """

    if not isinstance(shift, int):
        raise TypeError("shift must be an integer between 1 and 25")

    normalised = shift % _ALPHABET_SIZE
    if normalised == 0:
        raise ValueError("shift must be between 1 and 25")
    return normalised


def caesar(text: str, shift: int, *, encode: bool = True) -> str:
    """Apply a Caesar cipher rotation to ``text``."""

    normalised = _normalise_shift(shift)
    if not encode:
        normalised = (-normalised) % _ALPHABET_SIZE

    shifted_lower = LOWER_ALPHABET[normalised:] + LOWER_ALPHABET[:normalised]
    shifted_upper = UPPER_ALPHABET[normalised:] + UPPER_ALPHABET[:normalised]

    translation_table = str.maketrans(
        LOWER_ALPHABET + UPPER_ALPHABET,
        shifted_lower + shifted_upper,
    )
    return text.translate(translation_table)


def encode(text: str, shift: int) -> str:
    """Encode plain-text using a positive shift."""

    return caesar(text, shift, encode=True)


def decode(text: str, shift: int) -> str:
    """Decode cipher-text that was previously encoded with the same shift."""

    return caesar(text, shift, encode=False)


def mapping_pairs(shift: int, *, encode: bool = True) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Return the mapping pairs for lowercase and uppercase alphabets."""

    normalised = _normalise_shift(shift)
    src_lower = LOWER_ALPHABET
    dst_lower = LOWER_ALPHABET[normalised:] + LOWER_ALPHABET[:normalised]

    src_upper = UPPER_ALPHABET
    dst_upper = UPPER_ALPHABET[normalised:] + UPPER_ALPHABET[:normalised]

    if not encode:
        src_lower, dst_lower = dst_lower, src_lower
        src_upper, dst_upper = dst_upper, src_upper

    return list(zip(src_lower, dst_lower)), list(zip(src_upper, dst_upper))


__all__ = [
    "LOWER_ALPHABET",
    "UPPER_ALPHABET",
    "caesar",
    "encode",
    "decode",
    "mapping_pairs",
]
