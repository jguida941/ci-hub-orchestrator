from types import SimpleNamespace

from cihub.cli import CommandResult
from cihub.commands import check as check_module


class FakeProc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _stub_success(_: SimpleNamespace) -> CommandResult:
    return CommandResult(exit_code=0, summary="ok")


def test_check_json_success(monkeypatch) -> None:
    monkeypatch.setattr(check_module, "cmd_preflight", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs", _stub_success)
    monkeypatch.setattr(check_module, "cmd_smoke", _stub_success)
    monkeypatch.setattr(check_module.subprocess, "run", lambda *a, **k: FakeProc())

    args = SimpleNamespace(
        json=True,
        smoke_repo=None,
        smoke_subdir=None,
        install_deps=False,
        relax=False,
        keep=False,
    )
    result = check_module.cmd_check(args)

    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    step_names = [step["name"] for step in result.data["steps"]]
    assert step_names == [
        "preflight",
        "lint",
        "typecheck",
        "test",
        "actionlint",
        "docs-check",
        "smoke",
    ]


def test_check_failure_sets_exit(monkeypatch) -> None:
    monkeypatch.setattr(check_module, "cmd_preflight", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs", _stub_success)
    monkeypatch.setattr(check_module, "cmd_smoke", _stub_success)
    monkeypatch.setattr(
        check_module.subprocess, "run", lambda *a, **k: FakeProc(returncode=1)
    )

    args = SimpleNamespace(
        json=True,
        smoke_repo=None,
        smoke_subdir=None,
        install_deps=False,
        relax=False,
        keep=False,
    )
    result = check_module.cmd_check(args)

    assert isinstance(result, CommandResult)
    assert result.exit_code == 1
