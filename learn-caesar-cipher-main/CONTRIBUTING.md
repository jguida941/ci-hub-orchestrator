# Contributing

Thanks for your interest in improving the Caesar Cipher Learning Pack! The project has two tracks:

- `src/` — educational scripts and the PyQt6 demo.
- `caesar_cli/` — the production-ready command-line package.

## Quick start

1. Fork and clone the repository.
2. Create a virtual environment and install the CLI in editable mode:
   ```bash
   cd caesar_cli
   pip install -e .[dev]
   ```
3. Run the quality gates before submitting a pull request:
   ```bash
   ruff check
   mypy
   pytest --cov
   ```

## Coding guidelines

- Keep the educational scripts approachable with clear, beginner-friendly comments.
- Keep the CLI package pure and testable—business logic goes in `caesarcipher/core.py`.
- Maintain type hints and docstrings for all new public functions.
- Update `CHANGELOG.md` under the **Unreleased** section for every user-facing change.

## Commit messages & PRs

- Use clear, descriptive commit messages.
- Reference related issues when possible (e.g., `Fixes #42`).
- Include before/after screenshots or terminal output when updating the GUI or CLI UX.

## Code of Conduct

All contributors must follow the [Code of Conduct](CODE_OF_CONDUCT.md). If you see unacceptable behaviour, email `security@jguida.dev` or open a private issue.

Happy hacking!
