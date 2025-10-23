"""Application theming helpers."""

from __future__ import annotations

from PyQt6 import QtGui, QtWidgets

from caesarcipher.config.defaults import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    MUTED_COLOR,
    PANEL_BACKGROUND,
    TEXT_COLOR,
)


def apply_theme(app: QtWidgets.QApplication) -> None:
    """Apply the shared dark-style palette to the application."""
    app.setStyle("Fusion")

    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(BACKGROUND_COLOR))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#eeeeee"))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#101014"))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#1b1b22"))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor("#1b1b22"))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(TEXT_COLOR))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#18181e"))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#eeeeee"))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor("#ff6b6b"))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(ACCENT_COLOR))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#121212"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            background: #121212;
            color: #EEE;
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }
        QGroupBox {
            border: 1px solid #2D2D2D;
            border-radius: 10px;
            margin-top: 8px;
            padding: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            color: #00FFAA;
            font-weight: 600;
        }
        QLabel#mappingHint {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #1a1a1d, stop:1 #232327);
            border: 1px solid #2F2F2F;
            border-radius: 12px;
            padding: 8px 12px;
            font-size: 12px;
            color: #00FFAA;
            font-weight: 600;
        }
        QTextEdit, QPlainTextEdit, QListWidget, QTableWidget {
            background: #1F1F1F;
            border: 1px solid #2D2D2D;
            border-radius: 10px;
            padding: 6px;
            selection-background-color: #00FFAA;
            selection-color: #0A0A0A;
        }
        QSpinBox {
            background: #1F1F1F;
            border: 1px solid #2D2D2D;
            border-radius: 8px;
            padding: 4px;
        }
        QPushButton {
            background: #1F1F1F;
            border: 2px solid #2D2D2D;
            border-radius: 8px;
            padding: 8px 14px;
            min-width: 100px;
            color: #EEE;
            font-weight: 500;
        }
        QPushButton:hover {
            border-color: #00FFAA;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #1F1F1F, stop:1 #2F2F2F);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #2F2F2F, stop:1 #1F1F1F);
        }
        QPushButton#rot13Btn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #ff6b6b, stop:1 #ffa94d);
            border: none;
            color: #121212;
            font-weight: bold;
        }
        QPushButton#rot13Btn:hover {
            border: 2px solid #FFD700;
            margin: -1px;
        }
        QToolButton {
            color: #00FFAA;
            font-weight: 600;
            border: none;
            padding: 4px 6px;
        }
        QToolButton:hover {
            color: #7bffe2;
        }
        QToolButton:checked {
            color: #FFD54F;
        }
        QListWidget::item {
            padding: 6px 8px;
        }
        QListWidget::item:hover {
            background: rgba(0, 255, 170, 0.08);
        }
        QListWidget::item:selected {
            background: rgba(0, 255, 170, 0.25);
            color: #00FFAA;
        }
        QToolTip {
            background: #1E1E1E;
            color: #00FFAA;
            border: 1px solid #00FFAA;
            border-radius: 6px;
            padding: 6px;
        }
        """
    )


def style_panel(frame: QtWidgets.QWidget) -> None:
    """Apply consistent panel styling to containers."""
    frame.setStyleSheet(
        f"""
        QWidget#{frame.objectName()} {{
            background: {PANEL_BACKGROUND};
            border: 1px solid #2D2D2D;
            border-radius: 10px;
            padding: 12px 14px;
        }}
        """
    )


def accent_label(label: QtWidgets.QLabel, *, bold: bool = True) -> None:
    """Style headings that should use the accent cyan."""
    weight = "600" if bold else "400"
    label.setStyleSheet(
        f"color: {ACCENT_COLOR}; font-weight: {weight};"
    )


def muted_label(label: QtWidgets.QLabel) -> None:
    """Style supporting text with muted colour."""
    label.setStyleSheet(f"color: {MUTED_COLOR};")


__all__ = ["apply_theme", "style_panel", "accent_label", "muted_label"]
