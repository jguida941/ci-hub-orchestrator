"""Neon focus card displaying the currently highlighted mapping pair."""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets


class MappingFocusCard(QtWidgets.QFrame):
    """Shows the current mapping pair in a bold neon card."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mappingFocusCard")
        self.setFixedHeight(78)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(14)

        self.left_label = QtWidgets.QLabel("a")
        self.arrow_label = QtWidgets.QLabel("→")
        self.right_label = QtWidgets.QLabel("d")
        self.shift_label = QtWidgets.QLabel("shift +3")

        for lbl in (self.left_label, self.arrow_label, self.right_label):
            font = QtGui.QFont(self.font())
            font.setPointSize(24)
            font.setBold(True)
            lbl.setFont(font)
            lbl.setStyleSheet("background: transparent;")

        arrow_font = QtGui.QFont(self.arrow_label.font())
        arrow_font.setPointSize(22)
        self.arrow_label.setFont(arrow_font)

        shift_font = QtGui.QFont(self.font())
        shift_font.setPointSize(13)
        shift_font.setBold(True)
        self.shift_label.setFont(shift_font)
        self.shift_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.shift_label.setStyleSheet("color: #111111; background: transparent;")

        layout.addWidget(self.left_label)
        layout.addWidget(self.arrow_label)
        layout.addWidget(self.right_label)
        layout.addStretch()
        layout.addWidget(self.shift_label)

        self.setStyleSheet(
            """
            QFrame#mappingFocusCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #00ffbf, stop:0.52 #101010, stop:1 #ffa94d);
                border: 2px solid #ffa94d;
                border-radius: 14px;
            }
            QFrame#mappingFocusCard QLabel {
                color: #111111;
                background: transparent;
            }
            """
        )

    def update_focus(self, plain: str, cipher: str, shift: int, *, encode: bool) -> None:
        """Update the focus card with the current mapping."""
        self.left_label.setText((plain if encode else cipher).upper())
        self.right_label.setText((cipher if encode else plain).upper())
        arrow = "→" if encode else "←"
        self.arrow_label.setText(arrow)
        sign = "+" if encode else "-"
        if not encode:
            # In decode mode the shift is conceptually negative when moving back.
            sign = "-"
        self.shift_label.setText(f"shift {sign}{abs(shift)}")

    def reset_to_default(self, shift: int, encode: bool) -> None:
        """Display the default mapping for the current shift."""
        plain = "a"
        cipher = chr(((ord(plain) - ord("a") + shift) % 26) + ord("a"))
        self.update_focus(plain, cipher, shift, encode=encode)


__all__ = ["MappingFocusCard"]
