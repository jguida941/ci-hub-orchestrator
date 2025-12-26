"""Tests for wizard input validators."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.wizard.validators import (  # noqa: E402
    validate_package_name,
    validate_percentage,
    validate_repo_name,
    validate_version,
)


class TestValidatePercentage:
    """Tests for validate_percentage function."""

    @pytest.mark.parametrize(
        "value",
        ["0", "1", "50", "99", "100"],
    )
    def test_valid_percentages(self, value: str) -> None:
        """Valid percentage values return True."""
        assert validate_percentage(value) is True

    @pytest.mark.parametrize(
        "value,expected_msg",
        [
            ("-1", "Enter a value between 0 and 100."),
            ("-100", "Enter a value between 0 and 100."),
            ("101", "Enter a value between 0 and 100."),
            ("200", "Enter a value between 0 and 100."),
        ],
    )
    def test_out_of_range_returns_message(self, value: str, expected_msg: str) -> None:
        """Out of range values return error message."""
        result = validate_percentage(value)
        assert result == expected_msg

    @pytest.mark.parametrize(
        "value",
        ["abc", "", "12.5", "1.0", "  ", "fifty", "100%"],
    )
    def test_non_integer_returns_message(self, value: str) -> None:
        """Non-integer values return error message."""
        result = validate_percentage(value)
        assert result == "Enter a whole number (0-100)."

    def test_boundary_values(self) -> None:
        """Test exact boundary values."""
        assert validate_percentage("0") is True
        assert validate_percentage("100") is True
        assert validate_percentage("-1") == "Enter a value between 0 and 100."
        assert validate_percentage("101") == "Enter a value between 0 and 100."


class TestValidateVersion:
    """Tests for validate_version function."""

    @pytest.mark.parametrize(
        "value",
        ["3", "11", "17", "21", "3.11", "3.12", "17.0", "3.11.2", "21.0.1"],
    )
    def test_valid_versions(self, value: str) -> None:
        """Valid semver-ish versions return True."""
        assert validate_version(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            "3.11.2.1",  # too many segments
            "abc",
            "",
            "v3.11",  # has prefix
            "3.x",  # not numeric
            "3.11-beta",
            "3.",
            ".11",
        ],
    )
    def test_invalid_versions_return_message(self, value: str) -> None:
        """Invalid versions return error message."""
        result = validate_version(value)
        assert result == "Enter a version like 3, 3.11, or 3.11.2."

    def test_single_digit_version(self) -> None:
        """Single digit version is valid."""
        assert validate_version("3") is True

    def test_two_part_version(self) -> None:
        """Two part version is valid."""
        assert validate_version("3.12") is True

    def test_three_part_version(self) -> None:
        """Three part version is valid."""
        assert validate_version("3.12.1") is True


class TestValidatePackageName:
    """Tests for validate_package_name function."""

    @pytest.mark.parametrize(
        "value",
        [
            "mypackage",
            "my-package",
            "my_package",
            "my.package",
            "MyPackage",
            "package123",
            "123package",
            "a",
            "A",
            "0",
        ],
    )
    def test_valid_package_names(self, value: str) -> None:
        """Valid package names return True."""
        assert validate_package_name(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "-invalid",  # starts with dash
            ".invalid",  # starts with dot
            "_invalid",  # starts with underscore
            "invalid!",
            "invalid@name",
            "invalid name",
            "invalid/name",
        ],
    )
    def test_invalid_package_names_return_message(self, value: str) -> None:
        """Invalid package names return error message."""
        result = validate_package_name(value)
        assert result == "Use letters, numbers, ., -, or _."


class TestValidateRepoName:
    """Tests for validate_repo_name function."""

    @pytest.mark.parametrize(
        "value",
        [
            "myrepo",
            "my-repo",
            "my_repo",
            "my.repo",
            "MyRepo",
            "repo123",
            "123repo",
            "a",
            "A",
            "0",
        ],
    )
    def test_valid_repo_names(self, value: str) -> None:
        """Valid repo names return True."""
        assert validate_repo_name(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "invalid!",
            "invalid@repo",
            "invalid repo",
            "invalid/repo",
        ],
    )
    def test_invalid_repo_names_return_message(self, value: str) -> None:
        """Invalid repo names return error message."""
        result = validate_repo_name(value)
        assert result == "Use letters, numbers, ., -, or _."

    def test_repo_name_allows_leading_special_chars(self) -> None:
        """Repo name allows leading dots, dashes, underscores (unlike package)."""
        # This tests the difference between PACKAGE_RE and REPO_RE
        # REPO_RE allows [a-zA-Z0-9_.-]+ (any char can be first)
        # But actually looking at the regex, REPO_RE also starts with [a-zA-Z0-9_.-]+
        # which allows _ - . at start
        assert validate_repo_name("_repo") is True
        assert validate_repo_name("-repo") is True
        assert validate_repo_name(".repo") is True
