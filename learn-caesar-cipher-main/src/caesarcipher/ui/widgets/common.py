"""Common reusable widgets."""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets


class FocusAwarePlainTextEdit(QtWidgets.QPlainTextEdit):
    """PlainTextEdit variant emitting ``editingFinished`` when focus leaves."""

    editingFinished = QtCore.pyqtSignal()

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:  # type: ignore[override]
        super().focusOutEvent(event)
        self.editingFinished.emit()


__all__ = ["FocusAwarePlainTextEdit"]
