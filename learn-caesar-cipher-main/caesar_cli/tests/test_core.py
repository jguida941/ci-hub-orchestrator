import string

import pytest

from caesarcipher.core import caesar, decode, encode, mapping_pairs

SAMPLE_TEXTS = [
    "hello world",
    "Hello, Caesar Cipher!",
    string.ascii_letters,
    "1234-+= punctuation stays?",
]


@pytest.mark.parametrize("shift", range(1, 26))
def test_round_trip_preserves_text(shift: int) -> None:
    for text in SAMPLE_TEXTS:
        encoded = encode(text, shift)
        decoded = decode(encoded, shift)
        assert decoded == text


@pytest.mark.parametrize("shift", [1, 5, 13, 25])
def test_caesar_encode_then_decode_returns_original(shift: int) -> None:
    text = "Attack at dawn!"
    encoded = caesar(text, shift)
    twice = caesar(encoded, shift, encode=False)
    assert twice == text


def test_mapping_pairs_matches_encode_mode() -> None:
    lower, upper = mapping_pairs(3, encode=True)
    assert lower[0] == ("a", "d")
    assert upper[0] == ("A", "D")

    lower_dec, upper_dec = mapping_pairs(3, encode=False)
    assert lower_dec[0] == ("d", "a")
    assert upper_dec[0] == ("D", "A")


@pytest.mark.parametrize("bad_shift", [0, 26, 52, -26])
def test_invalid_shift_raises(bad_shift: int) -> None:
    with pytest.raises((TypeError, ValueError)):
        encode("abc", bad_shift)
