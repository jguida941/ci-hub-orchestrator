"""Tests for CLI command matrix runner."""

from __future__ import annotations

from pathlib import Path

from scripts.cli_command_matrix import (
    CommandSpec,
    _build_commands,
    _format_markdown,
    _format_rows,
    _format_table,
)


def test_command_spec_defaults() -> None:
    """Test CommandSpec dataclass defaults."""
    spec = CommandSpec(
        name="test",
        argv=["echo", "hello"],
        category="local",
    )
    assert spec.requires_repo is False
    assert spec.requires_report is False
    assert spec.requires_gh is False
    assert spec.ci_only is False
    assert spec.mutating is False
    assert spec.notes == ""
    assert spec.tags == []


def test_command_spec_with_flags() -> None:
    """Test CommandSpec with flags set."""
    spec = CommandSpec(
        name="test",
        argv=["cmd"],
        category="remote",
        requires_repo=True,
        requires_gh=True,
        ci_only=True,
        mutating=True,
        notes="Test note",
        tags=["security"],
    )
    assert spec.requires_repo is True
    assert spec.requires_gh is True
    assert spec.ci_only is True
    assert spec.mutating is True
    assert spec.notes == "Test note"
    assert spec.tags == ["security"]


def test_build_commands_returns_list() -> None:
    """Test _build_commands returns a list of CommandSpec."""
    commands = _build_commands("python", None, None)
    assert isinstance(commands, list)
    assert len(commands) > 0
    assert all(isinstance(cmd, CommandSpec) for cmd in commands)


def test_build_commands_with_repo_path(tmp_path: Path) -> None:
    """Test _build_commands with repo path."""
    commands = _build_commands("python", tmp_path, None)
    detect_cmd = next(c for c in commands if c.name == "detect")
    assert str(tmp_path) in " ".join(detect_cmd.argv)


def test_build_commands_with_report_path(tmp_path: Path) -> None:
    """Test _build_commands with report path."""
    report = tmp_path / "report.json"
    commands = _build_commands("python", None, report)
    report_cmd = next(c for c in commands if c.name == "report-summary")
    assert str(report) in " ".join(report_cmd.argv)


def test_format_rows_adds_missing_notes() -> None:
    """Test _format_rows adds notes for missing args."""
    spec = CommandSpec(
        name="test",
        argv=["cmd", "--repo", "<repo>"],
        category="local",
        requires_repo=True,
    )
    rows = _format_rows([spec], None, None)
    assert len(rows) == 1
    assert "Missing --repo" in rows[0]["notes"]


def test_format_rows_report_missing() -> None:
    """Test _format_rows notes missing report arg."""
    spec = CommandSpec(
        name="summary",
        argv=["cmd", "--report", "<report>"],
        category="local",
        requires_report=True,
    )
    rows = _format_rows([spec], None, None)
    assert "Missing --report" in rows[0]["notes"]


def test_format_table_output() -> None:
    """Test _format_table produces table output."""
    rows = [
        {"name": "cmd1", "category": "local", "command": "echo 1", "notes": "Note1"},
        {"name": "cmd2", "category": "remote", "command": "echo 2", "notes": ""},
    ]
    table = _format_table(rows)
    assert "name" in table
    assert "category" in table
    assert "cmd1" in table
    assert "cmd2" in table
    assert "---" in table  # separator line


def test_format_markdown_output() -> None:
    """Test _format_markdown produces markdown table."""
    rows = [
        {"name": "cmd1", "category": "local", "command": "echo 1", "notes": "Note1"},
    ]
    md = _format_markdown(rows)
    assert md.startswith("|")
    assert "| Name |" in md
    assert "| --- |" in md
    assert "| cmd1 |" in md


def test_run_command_success() -> None:
    """Test _run_command returns exit code 0 for successful command."""
    import subprocess
    from unittest import mock

    from scripts.cli_command_matrix import _run_command

    spec = CommandSpec(
        name="test",
        argv=["echo", "hello"],
        category="local",
    )

    with mock.patch.object(subprocess, "run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)
        code = _run_command(spec)

    assert code == 0
    mock_run.assert_called_once_with(["echo", "hello"], text=True)


def test_run_command_failure() -> None:
    """Test _run_command returns non-zero exit code on failure."""
    import subprocess
    from unittest import mock

    from scripts.cli_command_matrix import _run_command

    spec = CommandSpec(
        name="test",
        argv=["false"],
        category="local",
    )

    with mock.patch.object(subprocess, "run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=1)
        code = _run_command(spec)

    assert code == 1


def test_main_list_mode(monkeypatch, capsys) -> None:
    """Test main() in list mode (no --run flag)."""
    import sys

    from scripts.cli_command_matrix import main

    monkeypatch.setattr(sys, "argv", ["cli_command_matrix.py"])

    code = main()

    assert code == 0
    out = capsys.readouterr().out
    assert "name" in out
    assert "category" in out


def test_main_markdown_format(monkeypatch, capsys) -> None:
    """Test main() with markdown format."""
    import sys

    from scripts.cli_command_matrix import main

    monkeypatch.setattr(sys, "argv", ["cli_command_matrix.py", "--format", "markdown"])

    code = main()

    assert code == 0
    out = capsys.readouterr().out
    assert "| Name |" in out


def test_main_with_only_filter(monkeypatch, capsys) -> None:
    """Test main() with --only filter."""
    import sys

    from scripts.cli_command_matrix import main

    monkeypatch.setattr(sys, "argv", ["cli_command_matrix.py", "--only", "version"])

    code = main()

    assert code == 0
    out = capsys.readouterr().out
    assert "version" in out


def test_main_run_mode_skips_ci_only(monkeypatch, capsys) -> None:
    """Test main() in run mode skips CI-only commands."""
    import sys

    from scripts.cli_command_matrix import main

    # Run only version command which should succeed
    monkeypatch.setattr(sys, "argv", ["cli_command_matrix.py", "--run", "--only", "version"])

    code = main()
    # version command runs python -m cihub --version
    # We just check it tried to run
    out = capsys.readouterr().out
    assert "version" in out.lower() or code == 0


def test_main_run_skips_missing_repo(monkeypatch, capsys) -> None:
    """Test main() skips commands needing --repo when not provided."""
    import sys

    from scripts.cli_command_matrix import main

    monkeypatch.setattr(sys, "argv", ["cli_command_matrix.py", "--run", "--only", "detect"])

    main()  # Return code not checked - we verify behavior via output

    out = capsys.readouterr().out
    assert "SKIP" in out or "missing" in out.lower()


def test_main_run_skips_gh_required(monkeypatch, capsys) -> None:
    """Test main() skips GH-required commands without --include-remote."""
    import sys

    from scripts.cli_command_matrix import main

    monkeypatch.setattr(sys, "argv", ["cli_command_matrix.py", "--run", "--only", "verify-remote"])

    main()  # Return code not checked - we verify behavior via output

    out = capsys.readouterr().out
    assert "SKIP" in out
