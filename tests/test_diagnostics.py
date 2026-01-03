"""Tests for diagnostics models and renderers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.diagnostics.models import Diagnostic, DiagnosticSeverity  # noqa: E402
from cihub.diagnostics.renderer import format_console, format_editor  # noqa: E402

TEST_FILE = Path("/tmp/test.py")  # noqa: S108


class TestDiagnosticSeverity:
    """Tests for DiagnosticSeverity enum."""

    def test_severity_values(self) -> None:
        """Severity enum has expected values."""
        assert DiagnosticSeverity.ERROR.value == "error"
        assert DiagnosticSeverity.WARNING.value == "warning"
        assert DiagnosticSeverity.INFO.value == "info"
        assert DiagnosticSeverity.HINT.value == "hint"

    def test_severity_from_string(self) -> None:
        """Can create severity from string value."""
        assert DiagnosticSeverity("error") == DiagnosticSeverity.ERROR
        assert DiagnosticSeverity("warning") == DiagnosticSeverity.WARNING


class TestDiagnostic:
    """Tests for Diagnostic dataclass."""

    def test_create_minimal_diagnostic(self) -> None:
        """Create diagnostic with only required fields."""
        diag = Diagnostic(message="Test error")
        assert diag.message == "Test error"
        assert diag.severity == DiagnosticSeverity.ERROR
        assert diag.file is None
        assert diag.line is None
        assert diag.column is None
        assert diag.code is None
        assert diag.source is None
        assert diag.data == {}

    def test_create_full_diagnostic(self) -> None:
        """Create diagnostic with all fields."""
        diag = Diagnostic(
            message="Test error",
            severity=DiagnosticSeverity.WARNING,
            file=TEST_FILE,
            line=10,
            column=5,
            end_line=12,
            end_column=10,
            code="E001",
            source="ruff",
            data={"fix": "add import"},
        )
        assert diag.message == "Test error"
        assert diag.severity == DiagnosticSeverity.WARNING
        assert diag.file == TEST_FILE
        assert diag.line == 10
        assert diag.column == 5
        assert diag.end_line == 12
        assert diag.end_column == 10
        assert diag.code == "E001"
        assert diag.source == "ruff"
        assert diag.data == {"fix": "add import"}

    def test_to_dict_minimal(self) -> None:
        """to_dict() with minimal fields."""
        diag = Diagnostic(message="Test error")
        result = diag.to_dict()
        assert result == {
            "message": "Test error",
            "severity": "error",
        }

    def test_to_dict_full(self) -> None:
        """to_dict() with all fields."""
        diag = Diagnostic(
            message="Test error",
            severity=DiagnosticSeverity.WARNING,
            file=TEST_FILE,
            line=10,
            column=5,
            end_line=12,
            end_column=10,
            code="E001",
            source="ruff",
            data={"fix": "add import"},
        )
        result = diag.to_dict()
        assert result["message"] == "Test error"
        assert result["severity"] == "warning"
        assert result["file"] == str(TEST_FILE)
        assert result["line"] == 10
        assert result["column"] == 5
        assert result["end_line"] == 12
        assert result["end_column"] == 10
        assert result["code"] == "E001"
        assert result["source"] == "ruff"
        assert result["data"] == {"fix": "add import"}

    def test_from_dict_minimal(self) -> None:
        """from_dict() with minimal fields."""
        data = {"message": "Test error"}
        diag = Diagnostic.from_dict(data)
        assert diag.message == "Test error"
        assert diag.severity == DiagnosticSeverity.ERROR
        assert diag.file is None

    def test_from_dict_full(self) -> None:
        """from_dict() with all fields."""
        data = {
            "message": "Test error",
            "severity": "warning",
            "file": str(TEST_FILE),
            "line": 10,
            "column": 5,
            "end_line": 12,
            "end_column": 10,
            "code": "E001",
            "source": "ruff",
            "data": {"fix": "add import"},
        }
        diag = Diagnostic.from_dict(data)
        assert diag.message == "Test error"
        assert diag.severity == DiagnosticSeverity.WARNING
        assert diag.file == TEST_FILE
        assert diag.line == 10
        assert diag.column == 5
        assert diag.end_line == 12
        assert diag.end_column == 10
        assert diag.code == "E001"
        assert diag.source == "ruff"
        assert diag.data == {"fix": "add import"}

    def test_roundtrip_serialization(self) -> None:
        """to_dict() and from_dict() roundtrip preserves data."""
        original = Diagnostic(
            message="Test error",
            severity=DiagnosticSeverity.INFO,
            file=TEST_FILE,
            line=10,
            column=5,
            code="E001",
            source="mypy",
        )
        data = original.to_dict()
        restored = Diagnostic.from_dict(data)
        assert restored.message == original.message
        assert restored.severity == original.severity
        assert restored.file == original.file
        assert restored.line == original.line
        assert restored.column == original.column
        assert restored.code == original.code
        assert restored.source == original.source

    def test_to_dict_excludes_none_fields(self) -> None:
        """to_dict() excludes None optional fields."""
        diag = Diagnostic(message="Test", line=10)
        result = diag.to_dict()
        assert "file" not in result
        assert "column" not in result
        assert "code" not in result
        assert "line" in result

    def test_to_dict_excludes_empty_data(self) -> None:
        """to_dict() excludes empty data dict."""
        diag = Diagnostic(message="Test")
        result = diag.to_dict()
        assert "data" not in result


class TestFormatConsole:
    """Tests for format_console function."""

    def test_empty_diagnostics(self) -> None:
        """Empty list returns 'No issues found'."""
        result = format_console([])
        assert result == "No issues found."

    def test_single_minimal_diagnostic(self) -> None:
        """Format single diagnostic with minimal fields."""
        diag = Diagnostic(message="Test error")
        result = format_console([diag])
        assert "[ERROR]" in result
        assert "Test error" in result

    def test_diagnostic_with_file_and_line(self) -> None:
        """Format diagnostic with file and line info."""
        diag = Diagnostic(
            message="Test error",
            file=TEST_FILE,
            line=10,
        )
        result = format_console([diag])
        assert f"{TEST_FILE}:10" in result
        assert "Test error" in result

    def test_diagnostic_with_file_line_column(self) -> None:
        """Format diagnostic with file, line, and column."""
        diag = Diagnostic(
            message="Test error",
            file=TEST_FILE,
            line=10,
            column=5,
        )
        result = format_console([diag])
        assert f"{TEST_FILE}:10:5" in result

    def test_diagnostic_with_code(self) -> None:
        """Format diagnostic with error code."""
        diag = Diagnostic(message="Test error", code="E001")
        result = format_console([diag])
        assert "(E001)" in result

    def test_diagnostic_with_source(self) -> None:
        """Format diagnostic with source tool."""
        diag = Diagnostic(message="Test error", source="ruff")
        result = format_console([diag])
        assert "[ruff]" in result

    def test_multiple_diagnostics(self) -> None:
        """Format multiple diagnostics."""
        diags = [
            Diagnostic(message="Error 1", severity=DiagnosticSeverity.ERROR),
            Diagnostic(message="Warning 2", severity=DiagnosticSeverity.WARNING),
        ]
        result = format_console(diags)
        assert "[ERROR]" in result
        assert "[WARNING]" in result
        assert "Error 1" in result
        assert "Warning 2" in result
        lines = result.split("\n")
        assert len(lines) == 2

    def test_all_severity_levels(self) -> None:
        """All severity levels format correctly."""
        for severity in DiagnosticSeverity:
            diag = Diagnostic(message="Test", severity=severity)
            result = format_console([diag])
            assert f"[{severity.value.upper()}]" in result


class TestFormatEditor:
    """Tests for format_editor function (LSP format)."""

    def test_empty_diagnostics(self) -> None:
        """Empty list returns empty list."""
        result = format_editor([])
        assert result == []

    def test_single_minimal_diagnostic(self) -> None:
        """Format single diagnostic with minimal fields."""
        diag = Diagnostic(message="Test error")
        result = format_editor([diag])
        assert len(result) == 1
        assert result[0]["message"] == "Test error"
        assert result[0]["severity"] == 1  # error = 1

    def test_severity_mapping(self) -> None:
        """LSP severity mapping is correct."""
        severities = [
            (DiagnosticSeverity.ERROR, 1),
            (DiagnosticSeverity.WARNING, 2),
            (DiagnosticSeverity.INFO, 3),
            (DiagnosticSeverity.HINT, 4),
        ]
        for sev, expected in severities:
            diag = Diagnostic(message="Test", severity=sev)
            result = format_editor([diag])
            assert result[0]["severity"] == expected

    def test_file_becomes_uri(self) -> None:
        """File path becomes file:// URI."""
        diag = Diagnostic(message="Test", file=TEST_FILE)
        result = format_editor([diag])
        assert result[0]["uri"] == f"file://{TEST_FILE}"

    def test_line_number_conversion(self) -> None:
        """Line numbers convert from 1-based to 0-based."""
        diag = Diagnostic(message="Test", line=10, column=5)
        result = format_editor([diag])
        assert result[0]["range"]["start"]["line"] == 9  # 10 - 1
        assert result[0]["range"]["start"]["character"] == 4  # 5 - 1

    def test_range_with_end_position(self) -> None:
        """Range includes end position when provided."""
        diag = Diagnostic(
            message="Test",
            line=10,
            column=5,
            end_line=12,
            end_column=10,
        )
        result = format_editor([diag])
        assert result[0]["range"]["start"]["line"] == 9
        assert result[0]["range"]["start"]["character"] == 4
        assert result[0]["range"]["end"]["line"] == 11  # 12 - 1
        assert result[0]["range"]["end"]["character"] == 9  # 10 - 1

    def test_range_defaults_when_no_end(self) -> None:
        """Range uses start line for end when no end_line."""
        diag = Diagnostic(message="Test", line=10)
        result = format_editor([diag])
        assert result[0]["range"]["start"]["line"] == 9
        assert result[0]["range"]["end"]["line"] == 9
        assert result[0]["range"]["start"]["character"] == 0
        assert result[0]["range"]["end"]["character"] == 0

    def test_code_and_source(self) -> None:
        """Code and source are included when present."""
        diag = Diagnostic(message="Test", code="E001", source="ruff")
        result = format_editor([diag])
        assert result[0]["code"] == "E001"
        assert result[0]["source"] == "ruff"

    def test_no_code_source_when_missing(self) -> None:
        """Code and source are omitted when not provided."""
        diag = Diagnostic(message="Test")
        result = format_editor([diag])
        assert "code" not in result[0]
        assert "source" not in result[0]

    def test_multiple_diagnostics(self) -> None:
        """Multiple diagnostics are all formatted."""
        diags = [
            Diagnostic(message="Error 1"),
            Diagnostic(message="Error 2"),
        ]
        result = format_editor(diags)
        assert len(result) == 2
        assert result[0]["message"] == "Error 1"
        assert result[1]["message"] == "Error 2"


class TestDiagnosticMutationKillers:
    """Additional tests specifically to kill common mutations."""

    def test_to_dict_file_is_string_not_path(self) -> None:
        """Verify file is converted to string in to_dict()."""
        diag = Diagnostic(message="Test", file=TEST_FILE)
        result = diag.to_dict()
        assert isinstance(result["file"], str)
        assert result["file"] == str(TEST_FILE)

    def test_to_dict_empty_data_excluded(self) -> None:
        """Empty data dict is NOT included in to_dict()."""
        diag = Diagnostic(message="Test", data={})
        result = diag.to_dict()
        assert "data" not in result

    def test_to_dict_non_empty_data_included(self) -> None:
        """Non-empty data dict IS included in to_dict()."""
        diag = Diagnostic(message="Test", data={"key": "value"})
        result = diag.to_dict()
        assert "data" in result
        assert result["data"] == {"key": "value"}

    def test_from_dict_default_severity(self) -> None:
        """from_dict uses ERROR as default severity."""
        data = {"message": "Test"}
        diag = Diagnostic.from_dict(data)
        assert diag.severity == DiagnosticSeverity.ERROR

    def test_from_dict_empty_data_default(self) -> None:
        """from_dict uses empty dict for missing data."""
        data = {"message": "Test"}
        diag = Diagnostic.from_dict(data)
        assert diag.data == {}

    def test_format_console_location_with_line_only(self) -> None:
        """Console format with file and line but no column."""
        diag = Diagnostic(message="Error", file=TEST_FILE, line=10)
        result = format_console([diag])
        assert f"{TEST_FILE}:10 -" in result
        # Should NOT have column
        assert ":10:" not in result.replace(":10 -", "")

    def test_format_console_empty_strings_for_no_code_source(self) -> None:
        """Console format with no code/source produces no extra brackets."""
        diag = Diagnostic(message="Error")
        result = format_console([diag])
        assert "[ERROR]" in result
        assert "Error" in result
        # Should not have empty brackets like "() " or "[] "
        assert "() " not in result
        assert "[] Error" not in result

    def test_format_editor_severity_values(self) -> None:
        """All LSP severity values are correct numbers."""
        for sev, expected_num in [
            (DiagnosticSeverity.ERROR, 1),
            (DiagnosticSeverity.WARNING, 2),
            (DiagnosticSeverity.INFO, 3),
            (DiagnosticSeverity.HINT, 4),
        ]:
            diag = Diagnostic(message="Test", severity=sev)
            result = format_editor([diag])
            assert result[0]["severity"] == expected_num

    def test_format_editor_line_minus_one(self) -> None:
        """LSP line numbers are 0-based (line - 1)."""
        diag = Diagnostic(message="Test", line=1)
        result = format_editor([diag])
        assert result[0]["range"]["start"]["line"] == 0  # 1 - 1 = 0

        diag = Diagnostic(message="Test", line=100)
        result = format_editor([diag])
        assert result[0]["range"]["start"]["line"] == 99  # 100 - 1 = 99

    def test_format_editor_column_minus_one(self) -> None:
        """LSP column numbers are 0-based (column - 1)."""
        diag = Diagnostic(message="Test", line=1, column=1)
        result = format_editor([diag])
        assert result[0]["range"]["start"]["character"] == 0  # 1 - 1 = 0

        diag = Diagnostic(message="Test", line=1, column=50)
        result = format_editor([diag])
        assert result[0]["range"]["start"]["character"] == 49  # 50 - 1 = 49

    def test_format_editor_end_line_minus_one(self) -> None:
        """LSP end line is 0-based (end_line - 1)."""
        diag = Diagnostic(message="Test", line=1, end_line=5)
        result = format_editor([diag])
        assert result[0]["range"]["end"]["line"] == 4  # 5 - 1 = 4

    def test_format_editor_end_column_minus_one(self) -> None:
        """LSP end column is 0-based (end_column - 1)."""
        diag = Diagnostic(message="Test", line=1, end_line=5, end_column=20)
        result = format_editor([diag])
        assert result[0]["range"]["end"]["character"] == 19  # 20 - 1 = 19

    def test_format_editor_no_line_no_range(self) -> None:
        """No range when line is None."""
        diag = Diagnostic(message="Test")
        result = format_editor([diag])
        assert "range" not in result[0]

    def test_format_editor_file_becomes_uri(self) -> None:
        """File path has file:// prefix."""
        diag = Diagnostic(message="Test", file=TEST_FILE)
        result = format_editor([diag])
        assert result[0]["uri"].startswith("file://")
        assert str(TEST_FILE) in result[0]["uri"]

    def test_format_editor_no_file_no_uri(self) -> None:
        """No URI when file is None."""
        diag = Diagnostic(message="Test")
        result = format_editor([diag])
        assert "uri" not in result[0]
