from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys

import pytest

from caesarcipher import cli


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["-s", "3", "hello"], "khoor"),
        (["-d", "-s", "3", "khoor"], "hello"),
        (["--rot13", "uryyb"], "hello"),
    ],
)
def test_cli_happy_paths(argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    lines = captured.out.strip().splitlines()
    assert lines, "Expected output but got none"
    assert lines[-1] == expected


def test_cli_reads_from_stdin_and_shows_mapping(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", StringIO("azAZ"))
    exit_code = cli.main(["--show-mapping", "-s", "1"])
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert exit_code == 0
    assert lines, "Expected mapping output but got none"
    assert "Encoding mapping" in lines[0]
    assert lines[-1] == "baBA"


def test_cli_reads_from_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "plain.txt"
    source.write_text("hello", encoding="utf-8")
    exit_code = cli.main(["--input", str(source), "-s", "3"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "khoor"


def test_cli_writes_to_file(tmp_path: Path) -> None:
    dest = tmp_path / "cipher.txt"
    exit_code = cli.main(["-s", "3", "hello", "--output", str(dest)])
    assert exit_code == 0
    assert dest.read_text(encoding="utf-8") == "khoor"


def test_cli_no_color_flag(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--no-color", "-s", "3", "hello"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "khoor"


def test_cli_conflicting_text_and_input(tmp_path: Path) -> None:
    source = tmp_path / "plain.txt"
    source.write_text("hello", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        cli.main(["hello", "--input", str(source), "-s", "3"])
    assert exc.value.code == 2


def test_cli_about_exits_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--about"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Caesar CLI" in captured.out


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["-s", "0", "abc"],
        ["-s", "30", "abc"],
    ],
)
def test_cli_parser_errors_raise_system_exit(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert captured.err


def test_cli_catches_value_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def boom(*_: object, **__: object) -> str:
        raise ValueError("bad shift")

    monkeypatch.setattr(cli, "encode", boom)
    exit_code = cli.main(["-s", "3", "abc"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "bad shift" in captured.err


def test_cli_catches_unexpected_exception(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def kaboom(*_: object, **__: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "encode", kaboom)
    exit_code = cli.main(["-s", "4", "abc"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Unexpected error" in captured.err


def test_repl_encode_then_quit(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["", "3", "hello", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    exit_code = cli.repl()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "khoor" in captured.out


def test_repl_handles_unknown_mode(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["x", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    exit_code = cli.repl()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Unknown option" in captured.out


def test_repl_handles_invalid_shift(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["e", "abc", "e", "30", "e", "4", "hi", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    exit_code = cli.repl()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Shift must be an integer" in captured.out
    assert "Result" in captured.out


def test_repl_cancel_input(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["e", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    exit_code = cli.repl()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Cancelled." in captured.out


def test_repl_rot13_flow(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["r", "uryyb", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    exit_code = cli.repl()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "hello" in captured.out


def test_repl_toggle_mapping(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["e", "5", "abc", "m", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    exit_code = cli.repl()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Mapping display" in captured.out


def test_repl_initial_mapping(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["e", "3", "abc", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    exit_code = cli.repl(show_mapping=True)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Encoding mapping" in captured.out


def test_repl_encode_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["e", "4", "hello", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    def boom(text: str, shift: int) -> str:  # pragma: no cover - patched behaviour only
        raise ValueError("bad text")

    monkeypatch.setattr(cli, "encode", boom)
    exit_code = cli.repl()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "bad text" in captured.out


def test_main_auto_repl(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    inputs = iter(["", "3", "hello", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    exit_code = cli.main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "khoor" in captured.out
