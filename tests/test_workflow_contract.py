from types import SimpleNamespace

from cihub.cli import CommandResult, hub_root
from cihub.commands import verify as verify_module
from cihub.commands.verify import cmd_verify, validate_reusable_contracts, validate_template_contracts


def test_template_contracts_clean() -> None:
    problems, data = validate_template_contracts(hub_root())
    assert problems == []
    assert data["templates_checked"] > 0


def test_reusable_contracts_clean() -> None:
    problems, data = validate_reusable_contracts(hub_root())
    assert problems == []
    assert data["workflows"]


def test_cmd_verify_json_success() -> None:
    args = SimpleNamespace(json=True)
    result = cmd_verify(args)
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0


def test_cmd_verify_remote_includes_sync(monkeypatch) -> None:
    def fake_sync(**_kwargs) -> CommandResult:
        return CommandResult(exit_code=0, summary="ok", data={"repos": []})

    monkeypatch.setattr(verify_module, "_check_gh_auth", lambda: (True, ""))
    monkeypatch.setattr(verify_module, "_run_sync_check", fake_sync)

    args = SimpleNamespace(
        json=True,
        remote=True,
        integration=False,
        repo=None,
        include_disabled=False,
        install_deps=False,
        keep=False,
        workdir=None,
    )
    result = cmd_verify(args)
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert result.data["remote"] == {"repos": []}
