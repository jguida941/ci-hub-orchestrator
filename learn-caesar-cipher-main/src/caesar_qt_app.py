"""Legacy shim preserving the historical ``python -m src.caesar_qt_app`` entry point."""

from __future__ import annotations

from caesarcipher.app import run


__all__ = ["main", "run"]


def main() -> None:
    """Launch the refactored GUI via ``caesarcipher.app``."""
    run()


if __name__ == "__main__":
    main()
