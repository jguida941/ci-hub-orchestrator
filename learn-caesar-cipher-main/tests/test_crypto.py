import pytest

from caesarcipher.core.crypto import caesar


def test_caesar_encode_decode_roundtrip():
    text = "Hello, World!"
    for shift in range(1, 26):
        encoded = caesar(text, shift)
        decoded = caesar(encoded, shift, encode=False)
        assert decoded == text


def test_caesar_rejects_invalid_shift_type():
    with pytest.raises(TypeError):
        caesar("abc", "3")  # type: ignore[arg-type]


def test_caesar_rejects_out_of_range_shift():
    with pytest.raises(ValueError):
        caesar("abc", 0)
    with pytest.raises(ValueError):
        caesar("abc", 40)
