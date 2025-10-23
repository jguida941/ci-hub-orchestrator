"""
Caesar Cipher Example Using zip() and for Loop

This demonstrates how each letter in the alphabet maps to a new letter
when applying a Caesar cipher shift. Useful for visualizing letter rotation.
"""

alphabet = 'abcdefghijklmnopqrstuvwxyz'
shift = 5

# Build the shifted alphabet:
# 'fghijklmnopqrstuvwxyzabcde' (shifted 5 letters forward)
shifted_alphabet = alphabet[shift:] + alphabet[:shift]

print(f"Shift value: {shift}")
print(f"Original alphabet: {alphabet}")
print(f"Shifted  alphabet: {shifted_alphabet}\n")

# Example 1: Using zip()
#using zip zip() pairs the letters from both strings so you don't have to loop manually

print("Example 1 — Using zip():")
print("(zip pairs letters directly, e.g. a→f, b→g)\n")
for original, shifted in zip(alphabet, shifted_alphabet):
    print(f"{original} → {shifted}")

# Example 2: Using a for loop and looping manually
print("\nExample 2 — Using a for loop with indexes:")
for i in range(len(alphabet)):
    original = alphabet[i]
    shifted = shifted_alphabet[i]
    print(f"{original} → {shifted}")

