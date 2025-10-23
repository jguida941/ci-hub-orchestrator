"""Main window composition for the Caesar cipher GUI."""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from caesarcipher.config import defaults
from caesarcipher.logic.controller import CaesarController, ControllerDependencies
from caesarcipher.ui.widgets.common import FocusAwarePlainTextEdit
from caesarcipher.ui.widgets.history_panel import HistoryEntry, HistoryPanel
from caesarcipher.ui.widgets.info_panel import InfoPanel
from caesarcipher.ui.widgets.mapping_table import MappingTableWidget
from caesarcipher.ui.widgets.status_banner import StatusBanner
from caesarcipher.ui.widgets.mapping_focus_card import MappingFocusCard


class CaesarWindow(QtWidgets.QWidget):
    """Top-level widget hosting the Caesar cipher playground."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Caesar Cipher: Educational")
        self.setMinimumSize(960, 560)

        self.input_edit = FocusAwarePlainTextEdit()
        self.input_edit.setPlaceholderText("Enter text…")
        self.input_edit.setMinimumHeight(180)
        self.input_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.output_edit = QtWidgets.QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setToolTip("Cipher output appears here (read-only).")
        self.output_edit.setMinimumHeight(180)
        self.output_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        self.shift_spin = QtWidgets.QSpinBox()
        self.shift_spin.setRange(defaults.MIN_SHIFT, defaults.MAX_SHIFT)
        self.shift_spin.setValue(defaults.DEFAULT_SHIFT)
        self.shift_spin.setToolTip("Shift amount. Encoding uses (index + shift) mod 26; decoding uses (index - shift) mod 26.")

        self.encode_btn = QtWidgets.QRadioButton("Encode")
        self.encode_btn.setChecked(True)
        self.encode_btn.setToolTip("Encrypt by shifting letters forward: (index + shift) mod 26.")
        self.decode_btn = QtWidgets.QRadioButton("Decode")
        self.decode_btn.setToolTip("Decrypt by shifting letters backward: (index - shift) mod 26.")

        self.rot13_btn = QtWidgets.QPushButton("ROT13")
        self.rot13_btn.setObjectName("rot13Btn")
        self.rot13_btn.setToolTip("Set shift to 13 (ROT13 is its own inverse).")
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.reset_btn.setToolTip("Restore defaults: shift=3, encode mode, mapping hidden, fields cleared.")
        self.copy_btn = QtWidgets.QPushButton("Copy Result")
        self.copy_btn.setToolTip("Copy the current output text to the clipboard.")
        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.setToolTip("Clear both the input and output text areas.")
        self.show_map_chk = QtWidgets.QCheckBox("Show mapping")
        self.show_map_chk.setChecked(True)
        self.show_map_chk.setToolTip("Toggle the alphabet mapping grid for visualization.")

        self.status_banner = StatusBanner()
        self.info_panel = InfoPanel()
        self.mapping_table = MappingTableWidget()
        self.mapping_focus = MappingFocusCard(self)
        self.mapping_focus.hide()
        self.history_panel = HistoryPanel()
        self.history_panel.setToolTip("Double-click an item to reuse that result as new input.")
        self.info_toggle = QtWidgets.QToolButton()
        self.info_toggle.setText("Show Explanation ▾")
        self.info_toggle.setCheckable(True)
        self.info_toggle.setToolTip("Toggle a quick refresher on the modular arithmetic behind the shift.")
        toggle_style = """
            QRadioButton {
                background: #1F1F1F;
                border: 2px solid #2D2D2D;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QRadioButton::indicator { width: 0px; height: 0px; }
            QRadioButton:checked {
                background: #00FFAA;
                color: #000000;
                border: 2px solid #00FFAA;
            }
        """
        self.encode_btn.setStyleSheet(toggle_style)
        self.decode_btn.setStyleSheet(toggle_style)

        self._timer = QtCore.QTimer(self)
        self._info_visible = False

        self.mapping_stack = QtWidgets.QStackedWidget()
        self.mapping_stack.addWidget(self.mapping_table)
        self.mapping_stack.addWidget(self.info_panel)
        self.mapping_stack.setCurrentWidget(self.mapping_table)
        self.mapping_stack.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._adjust_mapping_stack_height(self.mapping_table)

        self.controller = CaesarController(
            ControllerDependencies(
                status_banner=self.status_banner,
                mapping_table=self.mapping_table,
                focus_card=self.mapping_focus,
                history_panel=self.history_panel,
                input_widget=self.input_edit,
                output_widget=self.output_edit,
                shift_spin=self.shift_spin,
                encode_button=self.encode_btn,
                decode_button=self.decode_btn,
                info_toggle=self.info_toggle,
                timer=self._timer,
            )
        )

        self._build_layout()
        self._wire_signals()
        self.info_toggle.setChecked(False)
        self.controller.run_cipher()

    def _build_layout(self) -> None:
        control_row = QtWidgets.QHBoxLayout()
        control_row.addWidget(QtWidgets.QLabel("Shift"))
        control_row.addWidget(self.shift_spin)
        control_row.addSpacing(12)
        control_row.addWidget(self.encode_btn)
        control_row.addWidget(self.decode_btn)
        control_row.addSpacing(12)
        control_row.addWidget(self.rot13_btn)
        control_row.addWidget(self.reset_btn)
        control_row.addStretch()
        control_row.addWidget(self.show_map_chk)
        control_row.addSpacing(12)
        control_row.addWidget(self.copy_btn)
        control_row.addWidget(self.clear_btn)

        top_section = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        top_layout.addWidget(QtWidgets.QLabel("Input"))
        top_layout.addWidget(self.input_edit)
        top_layout.addWidget(QtWidgets.QLabel("Output"))
        top_layout.addWidget(self.output_edit)
        top_layout.addWidget(self.status_banner)
        top_layout.addWidget(
            self.info_toggle, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        top_layout.setStretch(1, 1)
        top_layout.setStretch(3, 1)
        top_section.setMinimumHeight(340)
        top_section.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(top_section, stretch=1)
        left_layout.addWidget(self.mapping_stack)
        left_layout.setStretch(0, 1)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self.history_panel)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([820, 320])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.addLayout(control_row)
        root_layout.addWidget(splitter)

    def _wire_signals(self) -> None:
        self.input_edit.textChanged.connect(self.controller.run_cipher)
        self.input_edit.editingFinished.connect(self.controller.force_history_capture)
        self.shift_spin.valueChanged.connect(self.controller.run_cipher)
        self.encode_btn.toggled.connect(self.controller.run_cipher)
        self.decode_btn.toggled.connect(self.controller.run_cipher)
        self.show_map_chk.toggled.connect(self._toggle_mapping_visibility)
        self.info_toggle.toggled.connect(self._toggle_info_panel)
        self.rot13_btn.clicked.connect(self.controller.apply_rot13)
        self.reset_btn.clicked.connect(self.controller.reset)
        self.copy_btn.clicked.connect(self._copy_result)
        self.clear_btn.clicked.connect(self._clear_all)
        self.history_panel.entryActivated.connect(self._reuse_history_entry)
        self.mapping_table.cellDoubleClicked.connect(self._handle_mapping_double_click)
        self.info_panel.cardFlipRequested.connect(self._handle_info_double_click)
        # ensure visibility aligns with default view
        self._show_mapping_card()
        self.info_toggle.setChecked(False)
        self.status_banner.setVisible(True)
        self.mapping_stack.setVisible(True)
        # mapping focus card stays hidden; controller still updates it for consistency

    def _adjust_mapping_stack_height(self, widget: QtWidgets.QWidget) -> None:
        """Clamp the stacked widget height to its current child."""
        hint = max(1, widget.sizeHint().height())
        self.mapping_stack.setFixedHeight(hint)
        self.mapping_stack.updateGeometry()

    # Slots --------------------------------------------------------------
    def _copy_result(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.output_edit.toPlainText())

    def _clear_all(self) -> None:
        self.input_edit.clear()
        self.output_edit.clear()
        self.history_panel.clear()
        self.controller.run_cipher()

    def _reuse_history_entry(self, entry: HistoryEntry) -> None:
        if entry.mode == "ENC":
            self.decode_btn.setChecked(True)
        else:
            self.encode_btn.setChecked(True)
        self.shift_spin.setValue(entry.shift)
        self.input_edit.setPlainText(entry.result)
        self.input_edit.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.input_edit.setFocus()

    def _toggle_info_panel(self, checked: bool) -> None:
        if checked:
            self._show_info_card(from_toggle=True)
        else:
            self._show_mapping_card(from_toggle=True)
        self.info_toggle.setText("Hide Explanation ▴" if checked else "Show Explanation ▾")

    def _show_info_card(self, *, from_toggle: bool = False) -> None:
        self.mapping_stack.setCurrentWidget(self.info_panel)
        self._adjust_mapping_stack_height(self.info_panel)
        self._info_visible = True
        if not from_toggle:
            self.info_toggle.blockSignals(True)
            self.info_toggle.setChecked(True)
            self.info_toggle.blockSignals(False)
        self.info_toggle.setText("Hide Explanation ▴")

    def _show_mapping_card(self, *, from_toggle: bool = False) -> None:
        self.mapping_stack.setCurrentWidget(self.mapping_table)
        self._adjust_mapping_stack_height(self.mapping_table)
        self._info_visible = False
        if not from_toggle:
            self.info_toggle.blockSignals(True)
            self.info_toggle.setChecked(False)
            self.info_toggle.blockSignals(False)
        self.info_toggle.setText("Show Explanation ▾")

    def _handle_mapping_double_click(self, *_: int) -> None:
        self._show_info_card()

    def _handle_info_double_click(self) -> None:
        self._show_mapping_card()

    def _toggle_mapping_visibility(self, checked: bool) -> None:
        self.mapping_stack.setVisible(checked)
        self.status_banner.setVisible(checked)
        if checked:
            target = self.info_panel if self._info_visible else self.mapping_table
            self.mapping_stack.setCurrentWidget(target)
            self._adjust_mapping_stack_height(target)
        else:
            self._show_mapping_card()


__all__ = ["CaesarWindow"]
