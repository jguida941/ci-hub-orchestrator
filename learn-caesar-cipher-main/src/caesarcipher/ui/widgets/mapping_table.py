"""Mapping table widget for the Caesar cipher UI."""

from __future__ import annotations

from typing import cast

from PyQt6 import QtCore, QtGui, QtWidgets

from caesarcipher.config import defaults
from caesarcipher.core.crypto import LOWER


class MappingTableWidget(QtWidgets.QTableWidget):
    """Two-row table showing plain/cipher alphabet mapping."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(2, len(LOWER), parent)
        self._accent = QtGui.QColor(defaults.ACCENT_COLOR)
        self._muted_top = QtGui.QColor("#1a1f24")
        self._muted_bottom = QtGui.QColor("#15181d")
        self._text = QtGui.QColor(defaults.TEXT_COLOR)
        self._highlight_plain = QtGui.QColor("#00FFAA")
        self._highlight_plain.setAlpha(235)
        self._highlight_cipher = QtGui.QColor("#ffa94d")
        self._highlight_cipher.setAlpha(235)

        header = cast(QtWidgets.QHeaderView, self.horizontalHeader())
        header.setVisible(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

        v_header = cast(QtWidgets.QHeaderView, self.verticalHeader())
        v_header.setVisible(True)
        v_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Fixed)
        v_header.setMinimumSectionSize(0)
        v_header.setDefaultSectionSize(56)
        v_header.setStyleSheet(
            """
            QHeaderView::section {
                background: rgba(0, 0, 0, 0.0);
                font-weight: 600;
                padding-left: 12px;
                padding-right: 10px;
                border: none;
            }
            """
        )
        self._apply_header_labels(encode_mode=True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.setShowGrid(False)
        font = QtGui.QFont(self.font())
        font.setPointSize(14)
        font.setBold(True)
        font.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 1.6)
        self.setFont(font)
        self.setFixedHeight(150)
        self.setStyleSheet(
            """
            QTableWidget {
                background: #18191e;
                border: 1px solid #2D2D2D;
                border-radius: 10px;
                gridline-color: rgba(0, 0, 0, 0);
            }
            QTableWidget::item {
                padding: 2px 2px;
            }
            """
        )

        self._highlight_indices: set[int] = set()

    def set_highlights(self, indices: set[int]) -> None:
        """Store the indices to highlight on next update."""
        self._highlight_indices = indices

    def update_mapping(self, shifted: str, *, encode_mode: bool) -> None:
        """Render the alphabet rows with optional highlights."""
        top_row = LOWER if encode_mode else shifted
        bottom_row = shifted if encode_mode else LOWER
        self._apply_header_labels(encode_mode)

        highlight_plain = QtGui.QBrush(self._highlight_plain)
        highlight_cipher = QtGui.QBrush(self._highlight_cipher)
        muted_brush_top = QtGui.QBrush(self._muted_top)
        muted_brush_bottom = QtGui.QBrush(self._muted_bottom)
        text_brush = QtGui.QBrush(self._text)

        for index, (top_char, bottom_char) in enumerate(zip(top_row, bottom_row)):
            top_item = QtWidgets.QTableWidgetItem(top_char)
            top_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            top_item.setForeground(text_brush)
            top_highlight = highlight_plain if encode_mode else highlight_cipher
            top_item.setBackground(
                top_highlight if index in self._highlight_indices else muted_brush_top
            )
            top_item.setSizeHint(QtCore.QSize(top_item.sizeHint().width(), 52))

            bottom_item = QtWidgets.QTableWidgetItem(bottom_char)
            bottom_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            bottom_item.setForeground(text_brush)
            bottom_highlight = highlight_cipher if encode_mode else highlight_plain
            bottom_item.setBackground(
                bottom_highlight if index in self._highlight_indices else muted_brush_bottom
            )
            bottom_item.setSizeHint(QtCore.QSize(bottom_item.sizeHint().width(), 52))

            self.setItem(0, index, top_item)
            self.setItem(1, index, bottom_item)

        # no-op; height fixed via minimum height to mirror legacy UI

    def _apply_header_labels(self, encode_mode: bool) -> None:
        """Tint header labels to match accent colours for each row."""
        plain_item = QtWidgets.QTableWidgetItem("Plain")
        plain_item.setForeground(QtGui.QBrush(QtGui.QColor("#00FFAA")))
        cipher_item = QtWidgets.QTableWidgetItem("Cipher")
        cipher_item.setForeground(QtGui.QBrush(QtGui.QColor("#ffa94d")))

        if encode_mode:
            self.setVerticalHeaderItem(0, plain_item)
            self.setVerticalHeaderItem(1, cipher_item)
        else:
            self.setVerticalHeaderItem(0, cipher_item)
            self.setVerticalHeaderItem(1, plain_item)


__all__ = ["MappingTableWidget"]
