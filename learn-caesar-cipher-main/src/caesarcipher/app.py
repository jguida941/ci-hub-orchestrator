"""Application bootstrap for the Caesar cipher GUI."""

from __future__ import annotations

from PyQt6 import QtWidgets

from caesarcipher.ui.main_window import CaesarWindow
from caesarcipher.ui.theme import apply_theme


def run() -> None:
    """Launch the Caesar cipher GUI."""
    app = QtWidgets.QApplication([])
    apply_theme(app)
    window = CaesarWindow()
    window.show()
    app.exec()


__all__ = ["run"]
