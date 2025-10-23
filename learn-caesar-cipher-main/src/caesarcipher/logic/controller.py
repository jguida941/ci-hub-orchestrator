"""Controller coordinating UI widgets for the Caesar cipher GUI."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtCore

from caesarcipher.config import defaults
from caesarcipher.core.crypto import LOWER, caesar
from caesarcipher.ui.widgets.history_panel import HistoryEntry, HistoryPanel
from caesarcipher.ui.widgets.mapping_focus_card import MappingFocusCard
from caesarcipher.ui.widgets.mapping_table import MappingTableWidget
from caesarcipher.ui.widgets.status_banner import StatusBanner


@dataclass
class ControllerDependencies:
    status_banner: StatusBanner
    mapping_table: MappingTableWidget
    focus_card: MappingFocusCard
    history_panel: HistoryPanel
    input_widget: QtCore.QObject
    output_widget: QtCore.QObject
    shift_spin: QtCore.QObject
    encode_button: QtCore.QObject
    decode_button: QtCore.QObject
    info_toggle: QtCore.QObject
    timer: QtCore.QTimer


class CaesarController(QtCore.QObject):
    """Encapsulates the state transitions between widgets."""

    def __init__(self, deps: ControllerDependencies) -> None:
        super().__init__()
        self.deps = deps
        self._pending_history: HistoryEntry | None = None
        self._last_snapshot: HistoryEntry | None = None
        self._highlight_indices: set[int] = set()

        # Connect signals
        deps.timer.setSingleShot(True)
        deps.timer.timeout.connect(self._capture_history)

    # Public API ---------------------------------------------------------
    def reset(self) -> None:
        """Restore default state."""
        self._pending_history = None
        self._last_snapshot = None
        self.deps.history_panel.clear()
        self.deps.shift_spin.setValue(defaults.DEFAULT_SHIFT)  # type: ignore[attr-defined]
        self.deps.encode_button.setChecked(True)  # type: ignore[attr-defined]
        self.deps.input_widget.clear()  # type: ignore[attr-defined]
        self.deps.output_widget.setPlainText("")  # type: ignore[attr-defined]
        self.run_cipher()

    def apply_rot13(self) -> None:
        """Set shift to 13 and use encode mode."""
        self.deps.shift_spin.setValue(13)  # type: ignore[attr-defined]
        self.deps.encode_button.setChecked(True)  # type: ignore[attr-defined]
        self.run_cipher()

    def run_cipher(self) -> None:
        """Execute the Caesar cipher using current UI state."""
        text = self.deps.input_widget.toPlainText()  # type: ignore[attr-defined]
        shift = self.deps.shift_spin.value()  # type: ignore[attr-defined]
        encode = self.deps.encode_button.isChecked()  # type: ignore[attr-defined]

        shifted_lower = LOWER[shift:] + LOWER[:shift]
        indexes = _collect_indices(text, shifted_lower, encode)
        self._highlight_indices = indexes
        self.deps.mapping_table.set_highlights(indexes)
        self.deps.mapping_table.update_mapping(shifted_lower, encode_mode=encode)

        if not text:
            self.deps.output_widget.setPlainText("")  # type: ignore[attr-defined]
            self._pending_history = None
            self._last_snapshot = None
            self.deps.status_banner.set_mode(
                encode=encode,
                shift=shift,
                source_char=LOWER[0] if encode else shifted_lower[0],
                target_char=shifted_lower[0] if encode else LOWER[0],
            )
            self.deps.focus_card.reset_to_default(shift, encode)
            return

        result = caesar(text, shift, encode=encode)
        self.deps.output_widget.setPlainText(result)  # type: ignore[attr-defined]
        self.deps.status_banner.set_mode(
            encode=encode,
            shift=shift,
            source_char=LOWER[0] if encode else shifted_lower[0],
            target_char=shifted_lower[0] if encode else LOWER[0],
        )
        focus_index = _resolve_focus_index(text, encode, shifted_lower, indexes)
        plain_char = LOWER[focus_index]
        cipher_char = shifted_lower[focus_index]
        self.deps.focus_card.update_focus(plain_char, cipher_char, shift, encode=encode)

        entry = HistoryEntry(
            mode="ENC" if encode else "DEC",
            shift=shift,
            letters=sum(1 for ch in text if ch.isalpha()),
            words=len(text.split()),
            source=text,
            result=result,
        )
        self._pending_history = entry
        self._schedule_history_capture()

    # History handling ---------------------------------------------------
    def _schedule_history_capture(self) -> None:
        if not self._pending_history:
            self.deps.timer.stop()
            return
        self.deps.timer.start(450)

    def force_history_capture(self) -> None:
        if self._pending_history:
            self._capture_history(force=True)

    def _capture_history(self, force: bool = False) -> None:
        entry = self._pending_history
        if not entry:
            return
        if not force and self.deps.input_widget.hasFocus():  # type: ignore[attr-defined]
            return
        if self._last_snapshot == entry:
            return
        self.deps.history_panel.add_entry(entry)
        self._last_snapshot = entry


def _collect_indices(text: str, shifted_lower: str, encode: bool) -> set[int]:
    indices: set[int] = set()
    lookup = {char: idx for idx, char in enumerate(LOWER if encode else shifted_lower)}
    for char in text.lower():
        if char in lookup:
            indices.add(lookup[char])
    return indices


def _resolve_focus_index(
    text: str,
    encode: bool,
    shifted_lower: str,
    highlighted: set[int],
) -> int:
    if text:
        lowered = text.lower()
        if encode:
            for char in reversed(lowered):
                if char in LOWER:
                    return LOWER.index(char)
        else:
            for char in reversed(lowered):
                if char in shifted_lower:
                    return shifted_lower.index(char)
    if highlighted:
        fallback = min(highlighted)
        return max(0, min(25, fallback))
    return 0


__all__ = ["CaesarController", "ControllerDependencies"]
