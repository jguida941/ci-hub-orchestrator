"""History list widget matching the legacy UI styling."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtCore, QtWidgets

from caesarcipher.config.defaults import (
    HISTORY_LIMIT,
    HISTORY_PREVIEW_LENGTH,
    MONOSPACE_FALLBACK,
)


@dataclass(frozen=True)
class HistoryEntry:
    mode: str  # "ENC" or "DEC"
    shift: int
    letters: int
    words: int
    source: str
    result: str

    def label(self) -> str:
        preview_source = _preview(self.source, HISTORY_PREVIEW_LENGTH)
        preview_result = _preview(self.result, HISTORY_PREVIEW_LENGTH)
        arrow = "→" if self.mode == "ENC" else "←"
        return f"{preview_source} {arrow} {preview_result}"


def _preview(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    flattened = " ".join(text.split())
    if len(flattened) <= limit:
        return flattened
    return flattened[: max(1, limit - 1)].rstrip() + "…"


class HistoryPanel(QtWidgets.QListWidget):
    """Simple QListWidget helper storing the most recent transformations."""

    entryActivated = QtCore.pyqtSignal(HistoryEntry)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        max_entries: int = HISTORY_LIMIT,
    ) -> None:
        super().__init__(parent)
        self._max_entries = max_entries
        self._entries: list[HistoryEntry] = []
        self.setObjectName("historyList")
        self.list_widget = self  # compatibility with legacy tests
        self.setUniformItemSizes(True)
        self.setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)
        self.setFixedWidth(320)
        self.setStyleSheet(
            f"""
            QListWidget#historyList {{
                font-family: {MONOSPACE_FALLBACK};
                font-size: 10px;
            }}
            """
        )
        self.itemActivated.connect(self._emit_entry)

    def add_entry(self, entry: HistoryEntry) -> None:
        """Insert the new entry at the top and enforce the limit."""
        if self._entries and self._entries[0] == entry:
            return
        self._entries.insert(0, entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[: self._max_entries]
        self._refresh()

    def latest_entry(self) -> HistoryEntry | None:
        return self._entries[0] if self._entries else None

    def clear(self) -> None:  # type: ignore[override]
        self._entries.clear()
        super().clear()

    def _refresh(self) -> None:
        self.blockSignals(True)
        super().clear()
        for entry in self._entries:
            item = QtWidgets.QListWidgetItem(entry.label())
            item.setData(QtCore.Qt.ItemDataRole.UserRole, entry)
            item.setToolTip(
                f"{entry.mode} shift={entry.shift}\nLetters={entry.letters} Words={entry.words}\n{entry.source} → {entry.result}"
            )
            self.addItem(item)
        self.clearSelection()
        self.blockSignals(False)

    def _emit_entry(self, item: QtWidgets.QListWidgetItem) -> None:
        entry = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(entry, HistoryEntry):
            self.entryActivated.emit(entry)


__all__ = ["HistoryPanel", "HistoryEntry"]
