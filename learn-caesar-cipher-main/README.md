Caesar Cipher Learning Pack
================================

## Supply-chain Hardened Release Pipeline

This repository ships with a GitHub Actions workflow (`.github/workflows/release.yml`) that builds and signs a container image with full SBOM/provenance coverage:

- Multi-arch build and push to GHCR (`ghcr.io/jguida941/learn-caesar-cipher`).
- CycloneDX + SPDX SBOM generation via Syft.
- SLSA v1.0 provenance predicate (GitHub generator).
- Sigstore/cosign keyless signing for the pushed digest.
- OCI 1.1 referrers published for SBOM and provenance.
- Rekor inclusion proofs stored alongside release evidence.
- Rego policy gates verifying referrers, issuer/subject allowlists, and VEX status.

To run the pipeline, tag a release (e.g. `git tag v0.1.0 && git push origin v0.1.0`). Evidence artifacts will appear under the workflow run (`release-evidence`).

A hands-on set of Python scripts for teaching and experimenting with the classic Caesar cipher. The project walks learners from alphabet visualizations all the way to a simple interactive sandbox.  
> **Disclaimer:** This content is strictly educational and not intended for real cryptographic use.

![Kapture 2025-10-21 at 22 08 40](https://github.com/user-attachments/assets/4e91df38-ec17-4236-91f1-705ca67bf7e0)


![Kapture 2025-10-23 at 05 57 44](https://github.com/user-attachments/assets/6f90ea47-93f0-4505-a88f-d4b8681b9542)



Repository Layout
-----------------
```
.
├── README.md
├── updates.md                  # Packaging, CI, and release roadmap
├── caesar_cli/                 # Installable pip/pipx package scaffold (legacy tests)
├── src/
│   ├── __init__.py
│   ├── caesar_cipher.py        # Intermediate implementation
│   ├── caesar_educational.py   # Beginner-friendly walkthrough
│   ├── caesar_qt_app.py        # Legacy GUI shim (calls `caesarcipher.app.run`)
│   ├── interactive_demo.py     # Interactive encode/decode loop
│   ├── letter_mapping.py       # Alphabet rotation visualizer
│   └── caesarcipher/
│       ├── __init__.py
│       ├── app.py              # QApplication bootstrap
│       ├── cli.py              # CLI entry point (`caesar` command)
│       ├── py.typed
│       ├── config/
│       │   ├── __init__.py
│       │   └── defaults.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── crypto.py
│       ├── logic/
│       │   ├── __init__.py
│       │   └── controller.py
│       └── ui/
│           ├── __init__.py
│           ├── main_window.py
│           ├── theme.py
│           └── widgets/
│               ├── __init__.py
│               ├── common.py
│               ├── history_panel.py
│               ├── info_panel.py
│               ├── mapping_focus_card.py
│               ├── mapping_table.py
│               └── status_banner.py
└── tests/
    ├── conftest.py
    ├── test_crypto.py
    └── test_ui.py
```

Quick Start
-----------
**Prerequisites:** Python 3.8 or newer. A virtual environment is recommended (`python -m venv .venv && source .venv/bin/activate`).

1. Clone the repository.
2. (Optional) Activate your virtual environment.
   - Install extras as needed, e.g. `pip install PyQt6` to launch the GUI.
3. Run any script with Python 3.8+:
   ```bash
   python -m src.caesar_educational
   python -m src.letter_mapping
   python -m src.caesar_cipher
   python -m src.interactive_demo
   # Optional PyQt6 GUI (pip install PyQt6 first)
   python -m src.caesar_qt_app
   ```

4. Explore the modular package:
   ```bash
   python -m caesarcipher.app      # launch the refactored GUI
   python -m caesarcipher.cli -s 3 "hello"
   ```
   > Windows tip: PowerShell prefers double quotes (`"…"`); examples using single quotes need adjusting when copy/pasted.

To explore the new package scaffold:

```bash
cd caesar_cli
pip install -e .[dev]
caesar --help
caesar            # launches the interactive REPL (supply args to run once)
```

Sample Interactive Run
----------------------
```bash
$ python -m src.interactive_demo
Enter text to encode: hello world
Enter shift (1–25): 5
Type 'd' to decode, Type 'e' encode, or 'q' to quit: e

--- Interactive Result ---
Result: mjqqt btwqi
```

Choose Your Path
----------------
- **Beginner – `src/caesar_educational.py`**  
  Prints the full mapping for each shift, highlights lowercase/uppercase handling, and shows example encode/decode flows.
- **Visualization – `src/letter_mapping.py`**  
  Demonstrates alphabet rotation using both `zip()` pairing and manual index loops to reinforce how substitution ciphers work.
- **Intermediate – `src/caesar_cipher.py`**  
  Focuses on the core `caesar()` helper with concise validation and demonstrations of encode/decode helper functions.
- **Sandbox – `src/interactive_demo.py`**  
  Provides an infinite loop where learners can choose encode or decode, pick shift values, and experiment with their own phrases.
- **GUI – `src/caesar_qt_app.py`**  
  PyQt6 desktop application with a dark neon theme, live encode/decode preview, inline modular arithmetic explainer, ROT13 shortcut, mapping grid, and history panel (install PyQt6 to launch).
- **CLI Package – `caesar_cli/`**  
  Installable command-line tool (`caesar`) ready for pip/pipx packaging, complete with tests and optional extras.

Educational Highlights
----------------------
- Comments explain the **why** alongside the **what** so learners can follow reasoning.
- Examples show both lowercase and uppercase handling plus non-letter preservation.
- The interactive demo encourages experimentation without restarting the script.

What You’ll Learn
-----------------
- How substitution ciphers rotate alphabets and why valid shifts are 1–25.
- Using Python’s `str.maketrans()` and `str.translate()` to build mapping tables.
- Structuring helper functions (`encode_msg`, `decode_msg`) for clarity.
- Building simple command-line loops and validating user input.

Where to Go Next
----------------
- The forward-looking roadmap and packaging plan live in `updates.md`.
- Future work includes a polished CLI package (pip/pipx installable) and optional Homebrew wrapper as described in that document.
- Continuous integration is configured in `.github/workflows/ci.yml` (ruff, mypy, pytest, build).
- Local smoke tests: `ruff check`, `mypy src`, `pytest -q`.
- Contributions, suggestions, or classroom adaptations are welcome—feel free to open an issue or fork the repository.

Testing & CI Roadmap
--------------------
- Current scripts are instructional and can be explored module-by-module as shown above.
- The upgrade plan in `updates.md` documents the forthcoming CI pipeline with `ruff`, `mypy`, `pytest` + coverage gates, build checks, and optional mutation testing (`mutmut`).
- Property-based tests using Hypothesis (e.g., verifying encode/decode round-trips, ROT13 invariants, and non-letter handling) are slated for the next development cycle.
- Dev extras (`pytest`, `pytest-cov`, `mypy`, `ruff`, `hypothesis`, `build`, `twine`) will be exposed via `pyproject.toml` once the CLI packaging track begins.

Further Reading
---------------
- [Python `str.translate` documentation](https://docs.python.org/3/library/stdtypes.html#str.translate)
- [Python `str.maketrans` documentation](https://docs.python.org/3/library/stdtypes.html#str.maketrans)
- [An introduction to substitution ciphers](https://en.wikipedia.org/wiki/Substitution_cipher)
- [GeeksforGeeks: Caesar Cipher in Cryptography](https://www.geeksforgeeks.org/ethical-hacking/caesar-cipher-in-cryptography/)
- [FreeCodeCamp Caesar Cipher Workshop](https://www.freecodecamp.org/learn/full-stack-developer/workshop-caesar-cipher/step-1)
- [YouTube: Caesar Cipher Explained](https://www.youtube.com/watch?v=sMOZf4GN3oc)
