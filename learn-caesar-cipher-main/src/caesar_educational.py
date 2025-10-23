def caesar(text, shift, encoded=True, show_mapping=False):
    """
    Caesar Cipher Example

    Moves (shifts) each letter in your text forward in the alphabet
    by the number you choose. Works with both lowercase and uppercase.

    Example:
        If shift = 5:
            a → f
            b → g
            ...
            z → e
        (Same idea for uppercase: A → F, B → G, ...)
    """

    # Validate that shift is an integer
    # isinstance(shift, int) checks if shift is a number
    if not isinstance(shift, int):
        return 'Shift amount must be an integer.'

    # Ensure shift stays within valid range (1–25)
    # The alphabet has 26 letters, so shifting by 26 wraps back to the start (same as 0).
    # That leaves only 25 unique non-trivial rotations.
    if shift < 1 or shift > 25:
        return 'Shift amount must be between 1 and 25.'

    # Flip the shift direction when decoding so letters move backward
    if not encoded:
        shift = -shift

    # The alphabet in lowercase and uppercase
    lower_case = 'abcdefghijklmnopqrstuvwxyz'
    upper_case = lower_case.upper()

    # Shift the alphabet by the given amount
    # For example, if shift = 5:
    # 'abcdefghijklmnopqrstuvwxyz' → 'fghijklmnopqrstuvwxyzabcde'
    shifted_lower = lower_case[shift:] + lower_case[:shift]
    shifted_upper = upper_case[shift:] + upper_case[:shift]

    # Create a translation map for all letters
    # str.maketrans() connects each original letter to its shifted version
    translation_table = str.maketrans(
        lower_case + upper_case,
        shifted_lower + shifted_upper
    )
    encrypted_text = text.translate(translation_table)

    if show_mapping:
        print(f"Shift = {shift}")
        print("Lowercase mapping:")
        for letter, encoded_letter in zip(lower_case, shifted_lower):
            print(f"{letter} → {encoded_letter}")
        print("\nUppercase mapping:")
        for letter, encoded_letter in zip(upper_case, shifted_upper):
            print(f"{letter} → {encoded_letter}")
        print("-" * 30)

    return encrypted_text


# You can write a function to encode
def encode_msg(text, shift, show_mapping=False):
    return caesar(text, shift, show_mapping=show_mapping)


# function to decode
def decode_msg(text, shift, show_mapping=False):
    return caesar(text, shift, encoded=False, show_mapping=show_mapping)


if __name__ == "__main__":
    # Run this demo only when the file is executed directly
    print()  # visual spacer

    # Encode your messages here!
    example_text = "Scientific Computing is fun!"
    encoded_message = encode_msg(example_text, 3, show_mapping=True)
    # Decode your messages here!
    decoded_message = decode_msg("Vflhqwlilf Frpsxwlqj lv ixq!", 3)

    # Show the example round-trip before asking for interactive input
    print("\n--- Example Round-Trip ---")
    print(f"Original text: {example_text}")
    print(f"Encoded text : {encoded_message}")
    print(f"Decoded text : {decoded_message}")

