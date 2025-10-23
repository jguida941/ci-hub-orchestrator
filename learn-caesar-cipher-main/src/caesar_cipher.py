
"""
Simple Caesar Cipher.

Encrypts or decrypts text by shifting letters a specified number of positions.

Args:
    text (str): The text to encode or decode.
    shift (int): How many letters to shift by (1–25).
    encoded (bool): Whether to encode (True) or decode (False).

Notes:
    - Uses `isinstance` to ensure `shift` is an integer.
    - Valid shift values range from 1 to 25, covering the alphabet.
"""

def caesar(text, shift, encoded=True):
    # Validate that shift is an integer
    if not isinstance(shift, int):
        return 'Shift amount must be an integer.'

    # Ensure shift stays within alphabet range (1–25)
    if shift < 1 or shift > 25:
        return 'Shift amount must be between 1 and 25.'

    letters = 'abcdefghijklmnopqrstuvwxyz'

    # Reverse direction if decoding
    if not encoded:
        shift = -shift

    # Rotate alphabet by shift amount (e.g., shift=5 → ghijklmnopqrstuvwxyzabcde)
    shifted = letters[shift:] + letters[:shift]

    # Create translation map for lower and upper case.
    table = str.maketrans(letters + letters.upper(),
                          shifted + shifted.upper())

    # Apply translation
    return text.translate(table)


def encode_msg(text, shift):
    """Encrypt text using a Caesar cipher."""
    return caesar(text, shift)


def decode_msg(text, shift):
    """Decrypt text previously encoded with a Caesar cipher."""
    return caesar(text, shift, encoded=False)



# Encoding a message using our encode_msg function
encoded_msg = encode_msg('Hi my name is Justin', 13)
print(encoded_msg)

# Decoding our message using our decode_msg function
decoded_msg = decode_msg('Uv zl anzr vf Whfgva', 13)
print(decoded_msg)