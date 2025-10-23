from caesarcipher.ui.main_window import CaesarWindow
from caesarcipher.ui.widgets.history_panel import HistoryEntry, HistoryPanel
from caesarcipher.ui.widgets.mapping_table import MappingTableWidget


def test_history_panel_adds_and_limits_entries(qapp):
    panel = HistoryPanel(max_entries=3)
    for idx in range(5):
        entry = HistoryEntry(
            mode="ENC",
            shift=3,
            letters=idx + 1,
            words=1,
            source=f"text {idx}",
            result=f"cipher {idx}",
        )
        panel.add_entry(entry)

    assert panel.list_widget.count() == 3
    latest = panel.latest_entry()
    assert latest is not None
    assert latest.source == "text 4"


def test_mapping_table_updates_rows(qapp):
    table = MappingTableWidget()
    table.update_mapping("defghijklmnopqrstuvwxyzabc", encode_mode=True)
    assert table.item(0, 0).text() == "a"
    assert table.item(1, 0).text() == "d"

    table.update_mapping("defghijklmnopqrstuvwxyzabc", encode_mode=False)
    assert table.verticalHeaderItem(0).text() == "Cipher"
    assert table.item(0, 0).text() == "d"
    assert table.item(1, 0).text() == "a"


def test_window_controller_updates_output_and_history(qapp):
    window = CaesarWindow()
    window.input_edit.setPlainText("abc")
    window.controller.run_cipher()
    window.controller.force_history_capture()
    assert window.output_edit.toPlainText() == "def"
    latest = window.history_panel.latest_entry()
    assert latest is not None
    assert latest.result == "def"

    window.encode_btn.setChecked(False)
    window.decode_btn.setChecked(True)
    window.controller.run_cipher()
    window.controller.force_history_capture()
    assert window.output_edit.toPlainText() == "xyz"
    latest = window.history_panel.latest_entry()
    assert latest is not None
    assert latest.result == "xyz"

    window.close()
