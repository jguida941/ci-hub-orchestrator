"""Tests for cihub.commands.adr module."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from cihub.cli import CommandResult
from cihub.commands.adr import (
    ADR_PATTERN,
    _check_adr_links,
    _get_next_number,
    _link_is_external,
    _normalize_link_target,
    _parse_adr,
    _resolve_link,
    _slugify,
    _strip_fenced_blocks,
    cmd_adr,
    cmd_adr_check,
    cmd_adr_list,
    cmd_adr_new,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


class TestStripFencedBlocks:
    """Tests for _strip_fenced_blocks helper."""

    def test_removes_backtick_fenced_blocks(self) -> None:
        content = "Before\n```python\ncode\n```\nAfter"
        result = _strip_fenced_blocks(content)
        assert "code" not in result
        assert "Before" in result
        assert "After" in result

    def test_removes_tilde_fenced_blocks(self) -> None:
        content = "Before\n~~~yaml\nkey: value\n~~~\nAfter"
        result = _strip_fenced_blocks(content)
        assert "key: value" not in result

    def test_handles_multiple_blocks(self) -> None:
        content = "Start\n```\ncode_a\n```\nMiddle\n```\ncode_b\n```\nEnd"
        result = _strip_fenced_blocks(content)
        assert "code_a" not in result
        assert "code_b" not in result
        assert "Start" in result
        assert "End" in result


class TestLinkIsExternal:
    """Tests for _link_is_external helper."""

    def test_http_is_external(self) -> None:
        assert _link_is_external("http://example.com") is True

    def test_https_is_external(self) -> None:
        assert _link_is_external("https://github.com/repo") is True

    def test_mailto_is_external(self) -> None:
        assert _link_is_external("mailto:user@example.com") is True

    def test_tel_is_external(self) -> None:
        assert _link_is_external("tel:+1234567890") is True

    def test_relative_path_is_not_external(self) -> None:
        assert _link_is_external("./docs/file.md") is False
        assert _link_is_external("../other/file.md") is False

    def test_absolute_path_is_not_external(self) -> None:
        assert _link_is_external("/docs/file.md") is False


class TestNormalizeLinkTarget:
    """Tests for _normalize_link_target helper."""

    def test_strips_anchor(self) -> None:
        assert _normalize_link_target("file.md#section") == "file.md"

    def test_strips_query_string(self) -> None:
        assert _normalize_link_target("file.md?query=1") == "file.md"

    def test_strips_both_anchor_and_query(self) -> None:
        assert _normalize_link_target("file.md#section?param=value") == "file.md"

    def test_returns_empty_for_anchor_only(self) -> None:
        assert _normalize_link_target("#section") == ""


class TestResolveLink:
    """Tests for _resolve_link helper."""

    def test_resolves_absolute_path(self, tmp_path: Path) -> None:
        adr_path = tmp_path / "docs" / "adr" / "0001-test.md"
        adr_path.parent.mkdir(parents=True)
        adr_path.touch()

        result = _resolve_link(adr_path, tmp_path, "/README.md")
        assert result == (tmp_path / "README.md").resolve()

    def test_resolves_relative_path(self, tmp_path: Path) -> None:
        adr_path = tmp_path / "docs" / "adr" / "0001-test.md"
        adr_path.parent.mkdir(parents=True)
        adr_path.touch()

        result = _resolve_link(adr_path, tmp_path, "../guide.md")
        assert result == (tmp_path / "docs" / "guide.md").resolve()


class TestGetNextNumber:
    """Tests for _get_next_number function."""

    def test_returns_1_when_no_adr_dir(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            assert _get_next_number() == 1

    def test_returns_1_when_adr_dir_empty(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "adr").mkdir(parents=True)
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            assert _get_next_number() == 1

    def test_returns_next_after_existing(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-first.md").write_text("# ADR")
        (adr_dir / "0002-second.md").write_text("# ADR")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            assert _get_next_number() == 3

    def test_ignores_non_adr_files(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-first.md").write_text("# ADR")
        (adr_dir / "README.md").write_text("# Index")
        (adr_dir / "notes.txt").write_text("notes")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            assert _get_next_number() == 2


class TestSlugify:
    """Tests for _slugify helper."""

    def test_converts_to_lowercase(self) -> None:
        assert _slugify("Use REST API") == "use-rest-api"

    def test_removes_special_characters(self) -> None:
        assert _slugify("What's the plan?") == "whats-the-plan"

    def test_replaces_spaces_with_dashes(self) -> None:
        assert _slugify("multiple   spaces") == "multiple-spaces"

    def test_removes_underscores(self) -> None:
        # _slugify regex removes underscores, doesn't convert to dashes
        assert _slugify("use_snake_case") == "usesnakecase"

    def test_strips_leading_trailing_dashes(self) -> None:
        assert _slugify("-leading and trailing-") == "leading-and-trailing"

    def test_collapses_multiple_dashes(self) -> None:
        assert _slugify("a--b---c") == "a-b-c"


class TestAdrPattern:
    """Tests for ADR_PATTERN regex."""

    def test_matches_valid_adr_filename(self) -> None:
        assert ADR_PATTERN.match("0001-test-decision.md") is not None
        assert ADR_PATTERN.match("0099-another-one.md") is not None

    def test_extracts_number_and_slug(self) -> None:
        match = ADR_PATTERN.match("0042-use-python.md")
        assert match is not None
        assert match.group(1) == "0042"
        assert match.group(2) == "use-python"

    def test_does_not_match_invalid_formats(self) -> None:
        assert ADR_PATTERN.match("README.md") is None
        assert ADR_PATTERN.match("1-no-leading-zeros.md") is None


class TestParseAdr:
    """Tests for _parse_adr function."""

    def test_parses_complete_adr(self, tmp_path: Path) -> None:
        adr_path = tmp_path / "0001-test.md"
        adr_path.write_text(
            """# ADR-0001: Test Decision

**Status:** Accepted
**Date:** 2024-01-15

## Context
Some context here.
"""
        )

        result = _parse_adr(adr_path)
        assert result["file"] == "0001-test.md"
        assert result["number"] == 1
        assert result["title"] == "Test Decision"
        assert result["status"] == "Accepted"
        assert result["date"] == "2024-01-15"

    def test_handles_missing_status(self, tmp_path: Path) -> None:
        adr_path = tmp_path / "0002-no-status.md"
        adr_path.write_text("# ADR-0002: No Status\n\n## Context\n")

        result = _parse_adr(adr_path)
        assert result["status"] == "unknown"

    def test_handles_missing_date(self, tmp_path: Path) -> None:
        adr_path = tmp_path / "0003-no-date.md"
        adr_path.write_text("# ADR-0003: No Date\n\n**Status:** Proposed\n")

        result = _parse_adr(adr_path)
        assert result["date"] == ""

    def test_handles_non_adr_filename(self, tmp_path: Path) -> None:
        adr_path = tmp_path / "notes.md"
        adr_path.write_text("# Notes\n\n**Status:** Draft\n")

        result = _parse_adr(adr_path)
        assert result["number"] == 0
        assert result["title"] == "notes"  # Falls back to stem


class TestCheckAdrLinks:
    """Tests for _check_adr_links function."""

    def test_finds_broken_inline_link(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        adr_path = adr_dir / "0001-test.md"
        adr_path.write_text("# ADR\n\nSee [missing](./nonexistent.md) for details.\n")

        problems = _check_adr_links(adr_path)
        assert len(problems) == 1
        assert problems[0]["severity"] == "error"
        assert "nonexistent.md" in problems[0]["message"]

    def test_finds_broken_reference_link(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        adr_path = adr_dir / "0001-test.md"
        adr_path.write_text("# ADR\n\nSee [ref][ref-link] for details.\n\n[ref-link]: ./missing.md\n")

        problems = _check_adr_links(adr_path)
        assert len(problems) == 1
        assert "missing.md" in problems[0]["target"]

    def test_ignores_valid_links(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "other.md").write_text("# Other")

        adr_path = adr_dir / "0001-test.md"
        adr_path.write_text("# ADR\n\nSee [other](./other.md) for details.\n")

        problems = _check_adr_links(adr_path)
        assert len(problems) == 0

    def test_ignores_external_links(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        adr_path = adr_dir / "0001-test.md"
        adr_path.write_text("# ADR\n\nSee [GitHub](https://github.com).\n")

        problems = _check_adr_links(adr_path)
        assert len(problems) == 0

    def test_ignores_anchor_links(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        adr_path = adr_dir / "0001-test.md"
        adr_path.write_text("# ADR\n\nSee [section](#context).\n")

        problems = _check_adr_links(adr_path)
        assert len(problems) == 0

    def test_ignores_links_in_code_blocks(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        adr_path = adr_dir / "0001-test.md"
        adr_path.write_text("# ADR\n\n```markdown\n[broken](./missing.md)\n```\n")

        problems = _check_adr_links(adr_path)
        assert len(problems) == 0


class TestCmdAdrNew:
    """Tests for cmd_adr_new command."""

    def test_creates_new_adr(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(
                title="Use Python for CLI",
                dry_run=False,
                json=True,
            )
            result = cmd_adr_new(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["number"] == 1
        assert "0001-use-python-for-cli.md" in result.data["file"]

        # Verify file was created
        adr_path = tmp_path / "docs" / "adr" / "0001-use-python-for-cli.md"
        assert adr_path.exists()
        content = adr_path.read_text()
        assert "# ADR-0001: Use Python for CLI" in content
        assert "**Status**: Proposed" in content

    def test_requires_title(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(title="", dry_run=False, json=True)
            result = cmd_adr_new(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_FAILURE
        assert "Title is required" in result.summary

    def test_dry_run_does_not_create_file(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(
                title="Dry Run Test",
                dry_run=True,
                json=True,
            )
            result = cmd_adr_new(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert "Would create" in result.summary

        # File should NOT exist
        adr_dir = tmp_path / "docs" / "adr"
        assert not (adr_dir / "0001-dry-run-test.md").exists()

    def test_updates_readme_index(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        readme = adr_dir / "README.md"
        readme.write_text("# ADR Index\n\nTemplate starter:\n- Template\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(
                title="Test Entry",
                dry_run=False,
                json=True,
            )
            cmd_adr_new(args)

        content = readme.read_text()
        assert "- [ADR-0001: Test Entry](0001-test-entry.md)" in content

    def test_non_json_mode_prints_output(self, tmp_path: Path, capsys) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(
                title="Print Test",
                dry_run=False,
                json=False,
            )
            result = cmd_adr_new(args)

        assert result == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Created ADR:" in captured.out


class TestCmdAdrList:
    """Tests for cmd_adr_list command."""

    def test_lists_adrs(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-first.md").write_text("# ADR-0001: First\n\n**Status:** Accepted\n**Date:** 2024-01-01\n")
        (adr_dir / "0002-second.md").write_text("# ADR-0002: Second\n\n**Status:** Proposed\n**Date:** 2024-02-01\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(status=None, json=True)
            result = cmd_adr_list(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert len(result.data["adrs"]) == 2

    def test_filters_by_status(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-accepted.md").write_text("# ADR-0001: Accepted\n\n**Status:** Accepted\n")
        (adr_dir / "0002-proposed.md").write_text("# ADR-0002: Proposed\n\n**Status:** Proposed\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(status="Accepted", json=True)
            result = cmd_adr_list(args)

        assert len(result.data["adrs"]) == 1
        assert result.data["adrs"][0]["status"] == "Accepted"

    def test_returns_empty_when_no_adr_dir(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(status=None, json=True)
            result = cmd_adr_list(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["adrs"] == []

    def test_ignores_readme(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "README.md").write_text("# Index")
        (adr_dir / "0001-test.md").write_text("# ADR-0001: Test\n\n**Status:** Proposed\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(status=None, json=True)
            result = cmd_adr_list(args)

        assert len(result.data["adrs"]) == 1

    def test_non_json_mode_prints_table(self, tmp_path: Path, capsys) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-test.md").write_text("# ADR-0001: Test\n\n**Status:** Accepted\n**Date:** 2024-01-01\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(status=None, json=False)
            result = cmd_adr_list(args)

        assert result == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Accepted" in captured.out
        assert "Total: 1 ADRs" in captured.out


class TestCmdAdrCheck:
    """Tests for cmd_adr_check command."""

    def test_passes_with_valid_adrs(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "README.md").write_text("# Index")
        (adr_dir / "0001-valid.md").write_text("# ADR-0001: Valid\n\n**Status:** Accepted\n**Date:** 2024-01-01\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=True)
            result = cmd_adr_check(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert result.data["errors"] == 0

    def test_warns_on_missing_status(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "README.md").write_text("# Index")
        (adr_dir / "0001-no-status.md").write_text("# ADR-0001: No Status\n\n**Date:** 2024-01-01\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=True)
            result = cmd_adr_check(args)

        assert result.exit_code == EXIT_SUCCESS  # Warnings don't fail
        assert result.data["warnings"] == 1
        assert "Missing Status field" in result.problems[0]["message"]

    def test_warns_on_missing_date(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "README.md").write_text("# Index")
        (adr_dir / "0001-no-date.md").write_text("# ADR-0001: No Date\n\n**Status:** Proposed\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=True)
            result = cmd_adr_check(args)

        assert result.data["warnings"] == 1
        assert "Missing Date field" in result.problems[0]["message"]

    def test_warns_on_missing_readme(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-test.md").write_text("# ADR-0001: Test\n\n**Status:** Proposed\n**Date:** 2024-01-01\n")

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=True)
            result = cmd_adr_check(args)

        # Check for the README missing warning - code is "CIHUB-ADR-MISSING-README"
        assert any(p.get("code") == "CIHUB-ADR-MISSING-README" for p in result.problems)

    def test_fails_on_broken_links(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "README.md").write_text("# Index")
        (adr_dir / "0001-broken-link.md").write_text(
            "# ADR-0001: Broken\n\n**Status:** Proposed\n**Date:** 2024-01-01\n\nSee [missing](./nonexistent.md).\n"
        )

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=True)
            result = cmd_adr_check(args)

        assert result.exit_code == EXIT_FAILURE
        assert result.data["errors"] == 1

    def test_returns_ok_when_no_adr_dir(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=True)
            result = cmd_adr_check(args)

        assert isinstance(result, CommandResult)
        assert result.exit_code == EXIT_SUCCESS
        assert "No ADRs to check" in result.summary

    def test_non_json_mode_prints_problems(self, tmp_path: Path, capsys) -> None:
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-test.md").write_text("# ADR-0001: Test\n\n")  # Missing fields

        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(json=False)
            cmd_adr_check(args)

        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out


class TestCmdAdr:
    """Tests for cmd_adr router."""

    def test_routes_to_new(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(
                subcommand="new",
                title="Test",
                dry_run=True,
                json=True,
            )
            result = cmd_adr(args)

        assert isinstance(result, CommandResult)
        assert "Would create" in result.summary

    def test_routes_to_list(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(subcommand="list", status=None, json=True)
            result = cmd_adr(args)

        assert isinstance(result, CommandResult)
        assert "adrs" in result.data

    def test_routes_to_check(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(subcommand="check", json=True)
            result = cmd_adr(args)

        assert isinstance(result, CommandResult)

    def test_defaults_to_list(self, tmp_path: Path) -> None:
        with patch("cihub.commands.adr.hub_root", return_value=tmp_path):
            args = argparse.Namespace(subcommand=None, status=None, json=True)
            result = cmd_adr(args)

        assert isinstance(result, CommandResult)
        assert "adrs" in result.data
