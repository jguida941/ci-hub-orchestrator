from types import SimpleNamespace

from cihub.cli import CommandResult
from cihub.commands import check as check_module

FAST_STEPS = [
    "preflight",
    "ruff-lint",
    "ruff-format",
    "typecheck",
    "yamllint",
    "test",
    "actionlint",
    "docs-check",
    "smoke",
]
AUDIT_STEPS = ["docs-links", "adr-check", "validate-configs", "validate-profiles"]
SECURITY_STEPS = ["bandit", "pip-audit", "gitleaks", "trivy"]
FULL_STEPS = ["zizmor", "validate-templates", "verify-matrix-keys", "license-check"]
MUTATION_STEPS = ["mutmut"]


def _stub_success(*_args, **_kwargs) -> CommandResult:
    return CommandResult(exit_code=0, summary="ok")


def _run_check(monkeypatch, **flags) -> CommandResult:
    monkeypatch.setattr(check_module, "cmd_preflight", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs", _stub_success)
    monkeypatch.setattr(check_module, "cmd_smoke", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs_links", _stub_success)
    monkeypatch.setattr(check_module, "cmd_adr", _stub_success)
    monkeypatch.setattr(check_module, "_run_process", _stub_success)
    monkeypatch.setattr(check_module, "_run_optional", _stub_success)
    monkeypatch.setattr(check_module, "_run_zizmor", _stub_success)

    args = SimpleNamespace(
        json=True,
        smoke_repo=None,
        smoke_subdir=None,
        install_deps=False,
        relax=False,
        keep=False,
        audit=False,
        security=False,
        full=False,
        mutation=False,
        all=False,
    )
    for key, value in flags.items():
        setattr(args, key, value)

    result = check_module.cmd_check(args)
    assert isinstance(result, CommandResult)
    return result


def test_check_json_success_default(monkeypatch) -> None:
    result = _run_check(monkeypatch)

    assert result.exit_code == 0
    step_names = [step["name"] for step in result.data["steps"]]
    assert step_names == FAST_STEPS
    assert result.data["modes"] == {
        "audit": False,
        "security": False,
        "full": False,
        "mutation": False,
    }


def test_check_json_with_audit(monkeypatch) -> None:
    result = _run_check(monkeypatch, audit=True)

    assert result.exit_code == 0
    step_names = [step["name"] for step in result.data["steps"]]
    assert step_names == FAST_STEPS + AUDIT_STEPS
    assert result.data["modes"]["audit"] is True


def test_check_json_with_security(monkeypatch) -> None:
    result = _run_check(monkeypatch, security=True)

    assert result.exit_code == 0
    step_names = [step["name"] for step in result.data["steps"]]
    assert step_names == FAST_STEPS + SECURITY_STEPS
    assert result.data["modes"]["security"] is True


def test_check_json_with_full(monkeypatch) -> None:
    result = _run_check(monkeypatch, full=True)

    assert result.exit_code == 0
    step_names = [step["name"] for step in result.data["steps"]]
    assert step_names == FAST_STEPS + FULL_STEPS
    assert result.data["modes"]["full"] is True


def test_check_json_with_mutation(monkeypatch) -> None:
    result = _run_check(monkeypatch, mutation=True)

    assert result.exit_code == 0
    step_names = [step["name"] for step in result.data["steps"]]
    assert step_names == FAST_STEPS + MUTATION_STEPS
    assert result.data["modes"]["mutation"] is True


def test_check_json_with_all(monkeypatch) -> None:
    result = _run_check(monkeypatch, all=True)

    assert result.exit_code == 0
    step_names = [step["name"] for step in result.data["steps"]]
    assert step_names == (FAST_STEPS + AUDIT_STEPS + SECURITY_STEPS + FULL_STEPS + MUTATION_STEPS)
    assert result.data["modes"] == {
        "audit": True,
        "security": True,
        "full": True,
        "mutation": True,
    }


def test_check_failure_sets_exit(monkeypatch) -> None:
    monkeypatch.setattr(check_module, "cmd_preflight", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs", _stub_success)
    monkeypatch.setattr(check_module, "cmd_smoke", _stub_success)
    monkeypatch.setattr(
        check_module,
        "_run_process",
        lambda *_a, **_k: CommandResult(exit_code=1, summary="failed"),
    )
    monkeypatch.setattr(check_module, "_run_optional", _stub_success)

    args = SimpleNamespace(
        json=True,
        smoke_repo=None,
        smoke_subdir=None,
        install_deps=False,
        relax=False,
        keep=False,
        audit=False,
        security=False,
        full=False,
        mutation=False,
        all=False,
    )
    result = check_module.cmd_check(args)

    assert isinstance(result, CommandResult)
    assert result.exit_code == 1


def test_check_pytest_command_includes_coverage_gate(monkeypatch) -> None:
    """Verify pytest command includes --cov-fail-under=70 for CI parity.

    This test ensures the coverage gate is enforced locally,
    catching the issue where CI failed but local check passed.
    """
    captured_cmds: list[list[str]] = []

    def capture_run_process(name: str, cmd: list[str], cwd) -> CommandResult:
        captured_cmds.append((name, cmd))
        return CommandResult(exit_code=0, summary="ok")

    monkeypatch.setattr(check_module, "cmd_preflight", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs", _stub_success)
    monkeypatch.setattr(check_module, "cmd_smoke", _stub_success)
    monkeypatch.setattr(check_module, "cmd_docs_links", _stub_success)
    monkeypatch.setattr(check_module, "cmd_adr", _stub_success)
    monkeypatch.setattr(check_module, "_run_process", capture_run_process)
    monkeypatch.setattr(check_module, "_run_optional", _stub_success)

    args = SimpleNamespace(
        json=True,
        smoke_repo=None,
        smoke_subdir=None,
        install_deps=False,
        relax=False,
        keep=False,
        audit=False,
        security=False,
        full=False,
        mutation=False,
        all=False,
    )
    check_module.cmd_check(args)

    # Find the test step command
    test_cmds = [(name, cmd) for name, cmd in captured_cmds if name == "test"]
    assert len(test_cmds) == 1, "Expected exactly one 'test' step"
    _, test_cmd = test_cmds[0]

    # Verify coverage flags are present
    assert "--cov=cihub" in test_cmd, "Missing --cov=cihub"
    assert "--cov=scripts" in test_cmd, "Missing --cov=scripts"
    assert "--cov-fail-under=70" in test_cmd, "Missing --cov-fail-under=70 - this is the CI parity gate!"
