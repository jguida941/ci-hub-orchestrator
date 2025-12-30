"""Run a local validation suite that mirrors CI gates."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cihub.cli import CommandResult, hub_root
from cihub.commands.docs import cmd_docs
from cihub.commands.preflight import cmd_preflight
from cihub.commands.smoke import cmd_smoke
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


@dataclass
class CheckStep:
    name: str
    exit_code: int
    summary: str
    problems: list[dict[str, Any]]


def _as_command_result(result: int | CommandResult) -> CommandResult:
    if isinstance(result, CommandResult):
        return result
    return CommandResult(exit_code=int(result))


def _tail_output(output: str, limit: int = 12) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def _run_process(name: str, cmd: list[str], cwd: Path) -> CommandResult:
    try:
        proc = subprocess.run(  # noqa: S603
            cmd,
            cwd=str(cwd),
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return CommandResult(
            exit_code=EXIT_FAILURE,
            summary=f"{cmd[0]} not found",
            problems=[
                {
                    "severity": "error",
                    "message": f"{name} failed (missing {cmd[0]})",
                    "command": " ".join(cmd),
                }
            ],
            suggestions=[
                {
                    "message": f"Install {cmd[0]} and re-run.",
                }
            ],
        )

    ok = proc.returncode == 0
    summary = "ok" if ok else f"failed (exit {proc.returncode})"
    problems: list[dict[str, Any]] = []
    if not ok:
        tail = _tail_output((proc.stdout or "") + (proc.stderr or ""))
        problems.append(
            {
                "severity": "error",
                "message": f"{name} failed",
                "detail": tail,
                "command": " ".join(cmd),
            }
        )

    return CommandResult(
        exit_code=EXIT_SUCCESS if ok else EXIT_FAILURE,
        summary=summary,
        problems=problems,
    )


def _format_line(step: CheckStep) -> str:
    status = "OK" if step.exit_code == 0 else "FAIL"
    summary = f": {step.summary}" if step.summary else ""
    return f"[{status}] {step.name}{summary}"


def cmd_check(args: argparse.Namespace) -> int | CommandResult:
    json_mode = getattr(args, "json", False)
    root = hub_root()

    steps: list[CheckStep] = []
    problems: list[dict[str, Any]] = []

    def add_step(name: str, result: int | CommandResult) -> None:
        outcome = _as_command_result(result)
        step = CheckStep(
            name=name,
            exit_code=outcome.exit_code,
            summary=outcome.summary,
            problems=outcome.problems,
        )
        steps.append(step)
        if outcome.exit_code != 0:
            problems.extend(outcome.problems)
        if not json_mode:
            print(_format_line(step))
            if outcome.exit_code != 0:
                for problem in outcome.problems:
                    detail = problem.get("detail") or problem.get("message")
                    if detail:
                        print(detail)

    preflight_args = argparse.Namespace(json=True, full=True)
    add_step("preflight", cmd_preflight(preflight_args))

    add_step("lint", _run_process("lint", ["ruff", "check", "."], root))
    add_step("typecheck", _run_process("typecheck", ["mypy", "cihub/", "scripts/"], root))
    add_step("test", _run_process("test", ["pytest", "tests/"], root))
    add_step(
        "actionlint",
        _run_process("actionlint", ["actionlint", ".github/workflows"], root),
    )

    docs_args = argparse.Namespace(
        subcommand="check",
        output="docs/reference",
        json=True,
    )
    add_step("docs-check", cmd_docs(docs_args))

    smoke_args = argparse.Namespace(
        repo=getattr(args, "smoke_repo", None),
        subdir=getattr(args, "smoke_subdir", None),
        type=None,
        all=False,
        full=True,
        install_deps=bool(getattr(args, "install_deps", False)),
        force=False,
        relax=bool(getattr(args, "relax", False)),
        keep=bool(getattr(args, "keep", False)),
        json=True,
    )
    add_step("smoke", cmd_smoke(smoke_args))

    failed = [step for step in steps if step.exit_code != 0]
    exit_code = EXIT_FAILURE if failed else EXIT_SUCCESS
    summary = (
        f"{len(failed)} checks failed" if failed else "All checks passed"
    )

    if json_mode:
        return CommandResult(
            exit_code=exit_code,
            summary=summary,
            problems=problems,
            data={
                "steps": [
                    {
                        "name": step.name,
                        "exit_code": step.exit_code,
                        "summary": step.summary,
                        "problems": step.problems,
                    }
                    for step in steps
                ]
            },
        )

    print(summary)
    return exit_code
