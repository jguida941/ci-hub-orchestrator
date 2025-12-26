"""Tests for python_ci_badges.py - Badge generation functionality."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.python_ci_badges import (  # noqa: E402
    _badge_dir,
    _badge_enabled,
    _count_color,
    _percent_color,
    count_badge,
    get_env_float,
    get_env_int,
    load_bandit,
    load_pip_audit,
    load_zizmor,
    main,
    percent_badge,
    status_badge,
)


class TestBadgeEnabled:
    """Tests for _badge_enabled function."""

    def test_enabled_with_true(self, monkeypatch):
        """Returns True when UPDATE_BADGES=true."""
        monkeypatch.setenv("UPDATE_BADGES", "true")
        assert _badge_enabled() is True

    def test_enabled_with_1(self, monkeypatch):
        """Returns True when UPDATE_BADGES=1."""
        monkeypatch.setenv("UPDATE_BADGES", "1")
        assert _badge_enabled() is True

    def test_enabled_with_yes(self, monkeypatch):
        """Returns True when UPDATE_BADGES=yes."""
        monkeypatch.setenv("UPDATE_BADGES", "yes")
        assert _badge_enabled() is True

    def test_disabled_when_not_set(self, monkeypatch):
        """Returns False when UPDATE_BADGES not set."""
        monkeypatch.delenv("UPDATE_BADGES", raising=False)
        assert _badge_enabled() is False

    def test_disabled_with_false(self, monkeypatch):
        """Returns False when UPDATE_BADGES=false."""
        monkeypatch.setenv("UPDATE_BADGES", "false")
        assert _badge_enabled() is False

    def test_case_insensitive(self, monkeypatch):
        """Check is case-insensitive."""
        monkeypatch.setenv("UPDATE_BADGES", "TRUE")
        assert _badge_enabled() is True


class TestBadgeDir:
    """Tests for _badge_dir function."""

    def test_default_dir(self, monkeypatch):
        """Returns default badges dir when not set."""
        monkeypatch.delenv("BADGE_OUTPUT_DIR", raising=False)
        result = _badge_dir()
        assert result.name == "badges"

    def test_custom_dir(self, monkeypatch, tmp_path: Path):
        """Returns custom dir when BADGE_OUTPUT_DIR set."""
        custom_dir = tmp_path / "custom_badges"
        monkeypatch.setenv("BADGE_OUTPUT_DIR", str(custom_dir))
        result = _badge_dir()
        assert result == custom_dir


class TestPercentColor:
    """Tests for _percent_color function."""

    @pytest.mark.parametrize(
        "percent,expected",
        [
            (100, "brightgreen"),
            (90, "brightgreen"),
            (89, "green"),
            (80, "green"),
            (79, "yellowgreen"),
            (70, "yellowgreen"),
            (69, "yellow"),
            (60, "yellow"),
            (59, "orange"),
            (50, "orange"),
            (49, "red"),
            (0, "red"),
        ],
    )
    def test_color_thresholds(self, percent, expected):
        """Correct color for each threshold."""
        assert _percent_color(percent) == expected


class TestCountColor:
    """Tests for _count_color function."""

    def test_zero_is_brightgreen(self):
        """Zero count returns brightgreen."""
        assert _count_color(0) == "brightgreen"

    def test_low_count_is_yellow(self):
        """Low count (1-5) returns yellow."""
        assert _count_color(3) == "yellow"
        assert _count_color(5) == "yellow"

    def test_medium_count_is_orange(self):
        """Medium count (6-10) returns orange."""
        assert _count_color(7) == "orange"
        assert _count_color(10) == "orange"

    def test_high_count_is_red(self):
        """High count (>10) returns red."""
        assert _count_color(11) == "red"
        assert _count_color(100) == "red"

    def test_custom_thresholds(self):
        """Custom thresholds work correctly."""
        # With thresholds (0, 2, 5) - stricter
        assert _count_color(1, thresholds=(0, 2, 5)) == "yellow"
        assert _count_color(3, thresholds=(0, 2, 5)) == "orange"
        assert _count_color(6, thresholds=(0, 2, 5)) == "red"


class TestPercentBadge:
    """Tests for percent_badge function."""

    def test_badge_structure(self):
        """Badge has correct structure."""
        badge = percent_badge("test", 85)
        assert badge["schemaVersion"] == 1
        assert badge["label"] == "test"
        assert badge["message"] == "85%"
        assert badge["color"] == "green"

    def test_clamps_to_100(self):
        """Values over 100 are clamped."""
        badge = percent_badge("test", 150)
        assert badge["message"] == "100%"

    def test_clamps_to_0(self):
        """Negative values are clamped to 0."""
        badge = percent_badge("test", -10)
        assert badge["message"] == "0%"


class TestCountBadge:
    """Tests for count_badge function."""

    def test_none_returns_na(self):
        """None count returns n/a badge."""
        badge = count_badge("test", None)
        assert badge["message"] == "n/a"
        assert badge["color"] == "lightgrey"

    def test_zero_returns_clean(self):
        """Zero count returns clean badge."""
        badge = count_badge("test", 0)
        assert badge["message"] == "clean"
        assert badge["color"] == "brightgreen"

    def test_positive_returns_count(self):
        """Positive count returns count with unit."""
        badge = count_badge("test", 5, "issues")
        assert badge["message"] == "5 issues"

    def test_custom_unit(self):
        """Custom unit appears in message."""
        badge = count_badge("test", 3, "errors")
        assert badge["message"] == "3 errors"


class TestStatusBadge:
    """Tests for status_badge function."""

    def test_badge_structure(self):
        """Badge has correct structure."""
        badge = status_badge("test", "passing", "green")
        assert badge["schemaVersion"] == 1
        assert badge["label"] == "test"
        assert badge["message"] == "passing"
        assert badge["color"] == "green"


class TestLoadZizmor:
    """Tests for load_zizmor function."""

    def test_missing_file_returns_none(self, monkeypatch):
        """Missing file returns None."""
        monkeypatch.delenv("ZIZMOR_SARIF", raising=False)
        # Point to non-existent default location
        with mock.patch(
            "scripts.python_ci_badges.ROOT", Path("/nonexistent")
        ):
            result = load_zizmor()
            assert result is None

    def test_empty_runs_returns_zero(self, tmp_path: Path, monkeypatch):
        """SARIF with empty runs returns 0."""
        sarif_file = tmp_path / "zizmor.sarif"
        sarif_file.write_text(json.dumps({"runs": []}))
        monkeypatch.setenv("ZIZMOR_SARIF", str(sarif_file))

        result = load_zizmor()
        assert result == 0

    def test_counts_error_and_warning(self, tmp_path: Path, monkeypatch):
        """Counts error and warning level findings."""
        sarif_file = tmp_path / "zizmor.sarif"
        sarif_file.write_text(
            json.dumps(
                {
                    "runs": [
                        {
                            "results": [
                                {"level": "error"},
                                {"level": "warning"},
                                {"level": "note"},  # Should not be counted
                            ]
                        }
                    ]
                }
            )
        )
        monkeypatch.setenv("ZIZMOR_SARIF", str(sarif_file))

        result = load_zizmor()
        assert result == 2

    def test_invalid_json_returns_none(self, tmp_path: Path, monkeypatch):
        """Invalid JSON returns None."""
        sarif_file = tmp_path / "zizmor.sarif"
        sarif_file.write_text("not valid json")
        monkeypatch.setenv("ZIZMOR_SARIF", str(sarif_file))

        result = load_zizmor()
        assert result is None


class TestLoadBandit:
    """Tests for load_bandit function."""

    def test_missing_file_returns_none(self, monkeypatch):
        """Missing file returns None."""
        with mock.patch(
            "scripts.python_ci_badges.ROOT", Path("/nonexistent")
        ):
            result = load_bandit()
            assert result is None

    def test_counts_high_severity(self, tmp_path: Path, monkeypatch):
        """Counts only HIGH severity issues."""
        with mock.patch("scripts.python_ci_badges.ROOT", tmp_path):
            bandit_file = tmp_path / "bandit.json"
            bandit_file.write_text(
                json.dumps(
                    {
                        "results": [
                            {"issue_severity": "HIGH"},
                            {"issue_severity": "HIGH"},
                            {"issue_severity": "MEDIUM"},
                            {"issue_severity": "LOW"},
                        ]
                    }
                )
            )

            result = load_bandit()
            assert result == 2

    def test_empty_results(self, tmp_path: Path, monkeypatch):
        """Empty results returns 0."""
        with mock.patch("scripts.python_ci_badges.ROOT", tmp_path):
            bandit_file = tmp_path / "bandit.json"
            bandit_file.write_text(json.dumps({"results": []}))

            result = load_bandit()
            assert result == 0


class TestLoadPipAudit:
    """Tests for load_pip_audit function."""

    def test_missing_file_returns_none(self):
        """Missing file returns None."""
        with mock.patch(
            "scripts.python_ci_badges.ROOT", Path("/nonexistent")
        ):
            result = load_pip_audit()
            assert result is None

    def test_list_format(self, tmp_path: Path):
        """Handles list format output."""
        with mock.patch("scripts.python_ci_badges.ROOT", tmp_path):
            audit_file = tmp_path / "pip-audit.json"
            audit_file.write_text(
                json.dumps(
                    [
                        {"name": "pkg1", "vulns": [{"id": "CVE-1"}, {"id": "CVE-2"}]},
                        {"name": "pkg2", "vulns": [{"id": "CVE-3"}]},
                    ]
                )
            )

            result = load_pip_audit()
            assert result == 3

    def test_dict_format(self, tmp_path: Path):
        """Handles dict format with dependencies key."""
        with mock.patch("scripts.python_ci_badges.ROOT", tmp_path):
            audit_file = tmp_path / "pip-audit.json"
            audit_file.write_text(
                json.dumps(
                    {
                        "dependencies": [
                            {"name": "pkg1", "vulns": [{"id": "CVE-1"}]},
                        ]
                    }
                )
            )

            result = load_pip_audit()
            assert result == 1

    def test_no_vulns_returns_zero(self, tmp_path: Path):
        """No vulnerabilities returns 0."""
        with mock.patch("scripts.python_ci_badges.ROOT", tmp_path):
            audit_file = tmp_path / "pip-audit.json"
            audit_file.write_text(json.dumps([{"name": "pkg1", "vulns": []}]))

            result = load_pip_audit()
            assert result == 0


class TestGetEnvInt:
    """Tests for get_env_int function."""

    def test_valid_int(self, monkeypatch):
        """Returns int for valid integer string."""
        monkeypatch.setenv("TEST_VAR", "42")
        assert get_env_int("TEST_VAR") == 42

    def test_invalid_int_returns_none(self, monkeypatch):
        """Returns None for non-integer string."""
        monkeypatch.setenv("TEST_VAR", "not-an-int")
        assert get_env_int("TEST_VAR") is None

    def test_missing_var_returns_none(self, monkeypatch):
        """Returns None for missing variable."""
        monkeypatch.delenv("TEST_VAR", raising=False)
        assert get_env_int("TEST_VAR") is None


class TestGetEnvFloat:
    """Tests for get_env_float function."""

    def test_valid_float(self, monkeypatch):
        """Returns float for valid float string."""
        monkeypatch.setenv("TEST_VAR", "85.5")
        assert get_env_float("TEST_VAR") == 85.5

    def test_valid_int_as_float(self, monkeypatch):
        """Returns float for integer string."""
        monkeypatch.setenv("TEST_VAR", "90")
        assert get_env_float("TEST_VAR") == 90.0

    def test_invalid_float_returns_none(self, monkeypatch):
        """Returns None for non-numeric string."""
        monkeypatch.setenv("TEST_VAR", "not-a-float")
        assert get_env_float("TEST_VAR") is None


class TestMain:
    """Tests for main function."""

    def test_disabled_returns_zero(self, monkeypatch, capsys):
        """Returns 0 when badge generation disabled."""
        monkeypatch.delenv("UPDATE_BADGES", raising=False)

        result = main()
        assert result == 0

        captured = capsys.readouterr()
        assert "Badge generation disabled" in captured.out

    def test_creates_badge_directory(self, tmp_path: Path, monkeypatch):
        """Creates badge directory if not exists."""
        badge_dir = tmp_path / "new_badges"
        monkeypatch.setenv("UPDATE_BADGES", "true")
        monkeypatch.setenv("BADGE_OUTPUT_DIR", str(badge_dir))
        monkeypatch.setenv("RUFF_ISSUES", "0")

        main()

        assert badge_dir.exists()

    def test_writes_badge_files(self, tmp_path: Path, monkeypatch):
        """Writes badge JSON files."""
        badge_dir = tmp_path / "badges"
        monkeypatch.setenv("UPDATE_BADGES", "true")
        monkeypatch.setenv("BADGE_OUTPUT_DIR", str(badge_dir))
        monkeypatch.setenv("RUFF_ISSUES", "5")
        monkeypatch.setenv("MUTATION_SCORE", "85")

        main()

        ruff_badge = json.loads((badge_dir / "ruff.json").read_text())
        assert ruff_badge["label"] == "ruff"
        assert ruff_badge["message"] == "5 issues"

        mutmut_badge = json.loads((badge_dir / "mutmut.json").read_text())
        assert mutmut_badge["label"] == "mutmut"
        assert mutmut_badge["message"] == "85%"

    def test_black_clean_status(self, tmp_path: Path, monkeypatch):
        """Black clean status creates clean badge."""
        badge_dir = tmp_path / "badges"
        monkeypatch.setenv("UPDATE_BADGES", "true")
        monkeypatch.setenv("BADGE_OUTPUT_DIR", str(badge_dir))
        monkeypatch.setenv("BLACK_STATUS", "clean")

        main()

        black_badge = json.loads((badge_dir / "black.json").read_text())
        assert black_badge["message"] == "clean"
        assert black_badge["color"] == "brightgreen"

    def test_black_failed_status(self, tmp_path: Path, monkeypatch):
        """Black failed status creates failed badge."""
        badge_dir = tmp_path / "badges"
        monkeypatch.setenv("UPDATE_BADGES", "true")
        monkeypatch.setenv("BADGE_OUTPUT_DIR", str(badge_dir))
        monkeypatch.setenv("BLACK_STATUS", "failed")

        main()

        black_badge = json.loads((badge_dir / "black.json").read_text())
        assert black_badge["message"] == "failed"
        assert black_badge["color"] == "red"
