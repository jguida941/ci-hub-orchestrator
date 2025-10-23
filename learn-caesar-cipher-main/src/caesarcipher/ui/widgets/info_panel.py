"""Informational panel explaining the Caesar cipher math."""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from caesarcipher.config.defaults import ACCENT_COLOR, TEXT_COLOR


class InfoPanel(QtWidgets.QFrame):
    """Panel containing the static 'How it works' explanation."""

    cardFlipRequested = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("infoPanel")

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.heading = QtWidgets.QLabel("How it works")
        self.heading.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.heading.setStyleSheet(
            f"color: {ACCENT_COLOR}; font-size: 16px; font-weight: 600;"
        )

        self.body = QtWidgets.QLabel()
        self.body.setWordWrap(True)
        self.body.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.body.setStyleSheet(
            f"color: {TEXT_COLOR}; font-size: 13px; line-height: 1.4;"
        )
        self.body.setText(
            "Encoding: (index + shift) mod 26 → wraps forward.\n"
            "Decoding: (index - shift) mod 26 → wraps backward.\n"
            "Shift values between 1–25 produce unique rotations; "
            "mod 26 keeps results in the 0–25 range so letters loop around the alphabet."
        )

        layout.addWidget(self.heading)
        layout.addWidget(self.body)

        self.setStyleSheet(
            """
            QFrame#infoPanel {
                background: rgba(18, 18, 18, 0.92);
                border: 1px solid #2D2D2D;
                border-radius: 10px;
            }
            QFrame#infoPanel QLabel {
                background: transparent;
            }
            """
        )

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.cardFlipRequested.emit()
        super().mouseDoubleClickEvent(event)


__all__ = ["InfoPanel"]
