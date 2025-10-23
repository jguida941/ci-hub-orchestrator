"""Status banner that displays the current mode/shift."""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class StatusBanner(QtWidgets.QLabel):
    """Pill-style banner describing encode/decode state."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mappingHint")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setMargin(0)
        self.setMinimumHeight(40)

    def set_mode(
        self,
        *,
        encode: bool,
        shift: int,
        source_char: str,
        target_char: str,
        plain_row: str | None = None,
        cipher_row: str | None = None,
    ) -> None:
        """Update the banner copy for the active mode."""
        mode = "Encode" if encode else "Decode"
        source_label = "plain" if encode else "cipher"
        target_label = "cipher" if encode else "plain"
        sign = "+" if encode else "-"
        text = (
            f"{mode} mode: {source_label} '{source_char}' → {target_label} '{target_char}' "
            f"(shift {sign}{shift}, mod 26)"
        )
        self.setText(text)


__all__ = ["StatusBanner"]
