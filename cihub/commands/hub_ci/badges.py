"""Badge generation and configuration output commands."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from cihub import badges as badge_tools
from cihub.cli import hub_root
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS

from . import (
    _bool_str,
    _compare_badges,
    _load_config,
    _resolve_output_path,
    _run_command,
    _write_outputs,
)


def cmd_badges(args: argparse.Namespace) -> int:
    import os

    root = hub_root()
    config_path = Path(args.config).resolve() if args.config else root / "config" / "defaults.yaml"
    config = _load_config(config_path)
    badges_cfg = config.get("reports", {}).get("badges", {}) or {}
    if badges_cfg.get("enabled") is False:
        print("Badges disabled via reports.badges.enabled")
        return EXIT_SUCCESS
    tools_cfg = config.get("hub_ci", {}).get("tools", {}) if isinstance(config.get("hub_ci"), dict) else {}

    def tool_enabled(name: str, default: bool = True) -> bool:
        if not isinstance(tools_cfg, dict):
            return default
        return bool(tools_cfg.get(name, default))

    # Collect disabled tools for deterministic "disabled" badges
    all_badge_tools = ["ruff", "mutmut", "mypy", "bandit", "pip_audit", "zizmor"]
    disabled_tools: set[str] = set()
    for tool in all_badge_tools:
        if not tool_enabled(tool):
            disabled_tools.add(tool)

    env = os.environ.copy()
    env["UPDATE_BADGES"] = "true"

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    if output_dir:
        env["BADGE_OUTPUT_DIR"] = str(output_dir)

    if args.ruff_issues is not None and tool_enabled("ruff"):
        env["RUFF_ISSUES"] = str(args.ruff_issues)
    if args.mutation_score is not None and tool_enabled("mutmut"):
        env["MUTATION_SCORE"] = str(args.mutation_score)
    if args.mypy_errors is not None and tool_enabled("mypy"):
        env["MYPY_ERRORS"] = str(args.mypy_errors)
    if args.black_issues is not None and tool_enabled("black"):
        env["BLACK_ISSUES"] = str(args.black_issues)
    if args.black_status and tool_enabled("black"):
        env["BLACK_STATUS"] = args.black_status
    if args.zizmor_sarif and tool_enabled("zizmor"):
        env["ZIZMOR_SARIF"] = str(Path(args.zizmor_sarif).resolve())

    artifacts_dir = Path(args.artifacts_dir).resolve() if args.artifacts_dir else None
    if artifacts_dir:
        bandit = artifacts_dir / "bandit-results" / "bandit.json"
        pip_audit = artifacts_dir / "pip-audit-results" / "pip-audit.json"
        zizmor = artifacts_dir / "zizmor-sarif" / "zizmor.sarif"
        if bandit.exists() and tool_enabled("bandit"):
            shutil.copyfile(bandit, root / "bandit.json")
        if pip_audit.exists() and tool_enabled("pip_audit"):
            shutil.copyfile(pip_audit, root / "pip-audit.json")
        if zizmor.exists() and tool_enabled("zizmor"):
            shutil.copyfile(zizmor, root / "zizmor.sarif")

    if args.check:
        with tempfile.TemporaryDirectory(prefix="cihub-badges-") as tmpdir:
            env["BADGE_OUTPUT_DIR"] = tmpdir
            result = badge_tools.main(env=env, root=root, disabled_tools=disabled_tools)
            if result != 0:
                return EXIT_FAILURE
            issues = _compare_badges(root / "badges", Path(tmpdir))
            if issues:
                print("Badge drift detected:")
                for issue in issues:
                    print(f"- {issue}")
                return EXIT_FAILURE
            print("Badges are up to date.")
            return EXIT_SUCCESS

    result = badge_tools.main(env=env, root=root, disabled_tools=disabled_tools)
    if result != 0:
        return EXIT_FAILURE
    return EXIT_SUCCESS


def cmd_badges_commit(_: argparse.Namespace) -> int:
    root = hub_root()
    message = "chore: update CI badges [skip ci]"

    def run_git(args: list[str]) -> "subprocess.CompletedProcess[str]":
        return _run_command(["git", *args], root)

    config_steps = (
        ["config", "user.name", "github-actions[bot]"],
        ["config", "user.email", "github-actions[bot]@users.noreply.github.com"],
    )
    for config_args in config_steps:
        proc = run_git(config_args)
        if proc.returncode != 0:
            message = (proc.stdout or proc.stderr or "").strip()
            if message:
                print(message, file=sys.stderr)
            return EXIT_FAILURE

    proc = run_git(["add", "badges/"])
    if proc.returncode != 0:
        message = (proc.stdout or proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    diff_proc = run_git(["diff", "--staged", "--quiet"])
    if diff_proc.returncode == 0:
        print("No badge changes to commit.")
        return EXIT_SUCCESS
    if diff_proc.returncode != 1:
        message = (diff_proc.stdout or diff_proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    commit_proc = run_git(["commit", "-m", message])
    if commit_proc.returncode != 0:
        message = (commit_proc.stdout or commit_proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    push_proc = run_git(["push"])
    if push_proc.returncode != 0:
        message = (push_proc.stdout or push_proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    return EXIT_SUCCESS


def cmd_outputs(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve() if args.config else hub_root() / "config" / "defaults.yaml"
    config = _load_config(config_path)
    hub_cfg = config.get("hub_ci", {}) if isinstance(config.get("hub_ci"), dict) else {}
    enabled = hub_cfg.get("enabled", True)
    tools = hub_cfg.get("tools", {}) if isinstance(hub_cfg.get("tools"), dict) else {}
    thresholds = hub_cfg.get("thresholds", {}) if isinstance(hub_cfg.get("thresholds"), dict) else {}

    outputs = {
        "hub_ci_enabled": _bool_str(bool(enabled)),
        "run_actionlint": _bool_str(bool(tools.get("actionlint", True))),
        "run_zizmor": _bool_str(bool(tools.get("zizmor", True))),
        "run_ruff": _bool_str(bool(tools.get("ruff", True))),
        "run_syntax": _bool_str(bool(tools.get("syntax", True))),
        "run_mypy": _bool_str(bool(tools.get("mypy", True))),
        "run_yamllint": _bool_str(bool(tools.get("yamllint", True))),
        "run_pytest": _bool_str(bool(tools.get("pytest", True))),
        "run_mutmut": _bool_str(bool(tools.get("mutmut", True))),
        "run_bandit": _bool_str(bool(tools.get("bandit", True))),
        "bandit_fail_high": _bool_str(bool(tools.get("bandit_fail_high", True))),
        "bandit_fail_medium": _bool_str(bool(tools.get("bandit_fail_medium", False))),
        "bandit_fail_low": _bool_str(bool(tools.get("bandit_fail_low", False))),
        "run_pip_audit": _bool_str(bool(tools.get("pip_audit", True))),
        "run_gitleaks": _bool_str(bool(tools.get("gitleaks", True))),
        "run_trivy": _bool_str(bool(tools.get("trivy", True))),
        "run_validate_templates": _bool_str(bool(tools.get("validate_templates", True))),
        "run_validate_configs": _bool_str(bool(tools.get("validate_configs", True))),
        "run_verify_matrix_keys": _bool_str(bool(tools.get("verify_matrix_keys", True))),
        "run_license_check": _bool_str(bool(tools.get("license_check", True))),
        "run_dependency_review": _bool_str(bool(tools.get("dependency_review", True))),
        "run_scorecard": _bool_str(bool(tools.get("scorecard", True))),
        "coverage_min": str(thresholds.get("coverage_min", 70)),
        "mutation_score_min": str(thresholds.get("mutation_score_min", 70)),
    }

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(outputs, output_path)
    return EXIT_SUCCESS
