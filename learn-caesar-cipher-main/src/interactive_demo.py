def caesar(text, shift, encoded=True):
    """
    Caesar Cipher Interactive Demo

    Demonstrates how a Caesar cipher shifts letters in text.
    Works with both lowercase and uppercase letters.
    Non-letter characters stay the same.

    Args:
        text (str): The message to encode or decode.
        shift (int): Number of positions to shift the alphabet (1–25).
        encoded (bool):
            True = encode (shift forward),
            False = decode (shift backward).

    Returns:
        str: The resulting encoded or decoded text.
    """

    if not isinstance(shift, int):
        return 'Shift amount must be an integer.'

    if shift < 1 or shift > 25:
        return 'Shift amount must be between 1 and 25.'

    if not encoded:
        shift = -shift

    lower_case = 'abcdefghijklmnopqrstuvwxyz'
    upper_case = lower_case.upper()


    shifted_lower = lower_case[shift:] + lower_case[:shift]
    shifted_upper = upper_case[shift:] + upper_case[:shift]

    translation_table = str.maketrans(
        lower_case + upper_case,
        shifted_lower + shifted_upper
    )
    encrypted_text = text.translate(translation_table)
    return encrypted_text


def encode_msg(text, shift):
    return caesar(text, shift)

def decode_msg(text, shift):
    return caesar(text, shift, encoded=False)



if __name__ == "__main__":
    while True:
        text_in = input("Enter text to encode/decode: ")
        shift_in = int(input("Enter shift (1–25): "))
        mode = input("Type 'd' to decode, Type 'e' encode, or 'q' to quit: ").lower()

        if mode == "q":
            print("Goodbye!")
            break

        # ensure only one letter and alphabetic
        if not mode.isalpha() or len(mode) != 1:
            print("Invalid input. Please enter one letter: 'd', 'e', or 'q'.")
            exit()

        if mode == "d":
            interactive_result = decode_msg(text_in, shift_in)
        elif mode == "e":
            interactive_result = encode_msg(text_in, shift_in)
        else:
            print("Invalid choice. Try again")
            continue

        print("\n--- Interactive Result ---")
        print(f"Result: {interactive_result}")

