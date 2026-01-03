"""Parser setup for core CLI commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def _add_preflight_parser(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
    name: str,
    help_text: str,
) -> None:
    parser = subparsers.add_parser(name, help=help_text)
    add_json_flag(parser)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Check optional toolchains and CI runners",
    )
    parser.set_defaults(func=handlers.cmd_preflight)


def add_core_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    detect = subparsers.add_parser("detect", help="Detect repo language and tools")
    add_json_flag(detect)
    detect.add_argument("--repo", required=True, help="Path to repo")
    detect.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    detect.add_argument("--explain", action="store_true", help="Show detection reasons")
    detect.set_defaults(func=handlers.cmd_detect)

    _add_preflight_parser(subparsers, add_json_flag, handlers, "preflight", "Check environment readiness")
    _add_preflight_parser(subparsers, add_json_flag, handlers, "doctor", "Alias for preflight")

    scaffold = subparsers.add_parser("scaffold", help="Generate a minimal fixture project")
    add_json_flag(scaffold)
    scaffold.add_argument(
        "type",
        nargs="?",
        help=("Fixture type (python-pyproject, python-setup, java-maven, java-gradle, monorepo)"),
    )
    scaffold.add_argument("path", nargs="?", help="Destination path")
    scaffold.add_argument("--list", action="store_true", help="List available fixture types")
    scaffold.add_argument("--force", action="store_true", help="Overwrite destination if not empty")
    scaffold.set_defaults(func=handlers.cmd_scaffold)

    smoke = subparsers.add_parser("smoke", help="Run a local smoke test")
    add_json_flag(smoke)
    smoke.add_argument(
        "repo",
        nargs="?",
        help="Path to repo (omit to scaffold fixtures)",
    )
    smoke.add_argument("--subdir", help="Subdirectory for monorepos")
    smoke.add_argument(
        "--type",
        action="append",
        help=(
            "Fixture type to generate (repeatable): python-pyproject, python-setup, java-maven, java-gradle, monorepo"
        ),
    )
    smoke.add_argument(
        "--all",
        action="store_true",
        help="Generate and test all fixture types",
    )
    smoke.add_argument(
        "--full",
        action="store_true",
        help="Run cihub ci after init/validate",
    )
    smoke.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during cihub ci",
    )
    smoke.add_argument(
        "--force",
        action="store_true",
        help="Allow init to overwrite existing .ci-hub.yml",
    )
    smoke.add_argument(
        "--relax",
        action="store_true",
        help="Relax tool toggles and thresholds when running full",
    )
    smoke.add_argument(
        "--keep",
        action="store_true",
        help="Keep generated fixtures on disk",
    )
    smoke.set_defaults(func=handlers.cmd_smoke)

    smoke_validate = subparsers.add_parser("smoke-validate", help="Validate smoke test setup/results")
    add_json_flag(smoke_validate)
    smoke_validate.add_argument("--count", type=int, help="Repo count to validate")
    smoke_validate.add_argument("--min-count", type=int, default=2, help="Minimum required repos")
    smoke_validate.add_argument("--status", help="Smoke test job status (success/failure)")
    smoke_validate.set_defaults(func=handlers.cmd_smoke_validate)

    check = subparsers.add_parser("check", help="Run local validation checks")
    add_json_flag(check)
    check.add_argument(
        "--smoke-repo",
        help="Path to repo for smoke test (omit to scaffold fixtures)",
    )
    check.add_argument(
        "--smoke-subdir",
        help="Subdirectory for monorepo smoke test",
    )
    check.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during smoke test",
    )
    check.add_argument(
        "--relax",
        action="store_true",
        help="Relax tool toggles and thresholds during smoke test",
    )
    check.add_argument(
        "--keep",
        action="store_true",
        help="Keep generated fixtures on disk",
    )
    check.add_argument(
        "--install-missing",
        action="store_true",
        help="Prompt to install missing optional tools",
    )
    check.add_argument(
        "--require-optional",
        action="store_true",
        help="Fail if optional tools are missing",
    )
    # Tiered check modes
    check.add_argument(
        "--audit",
        action="store_true",
        help="Add drift detection checks (links, adr, configs)",
    )
    check.add_argument(
        "--security",
        action="store_true",
        help="Add security checks (bandit, pip-audit, trivy, gitleaks)",
    )
    check.add_argument(
        "--full",
        action="store_true",
        help="Add validation checks (templates, matrix, license, zizmor)",
    )
    check.add_argument(
        "--mutation",
        action="store_true",
        help="Add mutation testing with mutmut (~15min, very slow)",
    )
    check.add_argument(
        "--all",
        action="store_true",
        help="Run all checks (audit + security + full + mutation)",
    )
    check.set_defaults(func=handlers.cmd_check)

    verify = subparsers.add_parser("verify", help="Verify workflow/template contracts")
    add_json_flag(verify)
    verify.add_argument(
        "--remote",
        action="store_true",
        help="Check connected repos for template drift (requires gh auth)",
    )
    verify.add_argument(
        "--integration",
        action="store_true",
        help="Clone connected repos and run cihub ci (slow, requires gh auth)",
    )
    verify.add_argument(
        "--repo",
        action="append",
        help="Target repo (owner/name). Repeatable.",
    )
    verify.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include repos with dispatch_enabled=false",
    )
    verify.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies during integration runs",
    )
    verify.add_argument(
        "--workdir",
        help="Optional base directory for cloned repos (integration mode)",
    )
    verify.add_argument(
        "--keep",
        action="store_true",
        help="Keep cloned repos on disk (integration mode)",
    )
    verify.set_defaults(func=handlers.cmd_verify)

    ci = subparsers.add_parser("ci", help="Run CI based on .ci-hub.yml")
    add_json_flag(ci)
    ci.add_argument("--repo", default=".", help="Path to repo (default: .)")
    ci.add_argument("--workdir", help="Override workdir/subdir")
    ci.add_argument("--correlation-id", help="Hub correlation id")
    ci.add_argument(
        "--config-from-hub",
        metavar="BASENAME",
        help="Load config from hub's config/repos/<BASENAME>.yaml (for hub-run-all)",
    )
    ci.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for reports (default: .cihub)",
    )
    ci.add_argument(
        "--install-deps",
        action="store_true",
        help="Install repo dependencies before running tools",
    )
    ci.add_argument("--report", help="Override report.json path")
    ci.add_argument("--summary", help="Override summary.md path")
    ci.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip writing summary.md file",
    )
    ci.add_argument(
        "--write-github-summary",
        action="store_true",
        default=None,
        help="Write summary to GITHUB_STEP_SUMMARY if set (overrides config)",
    )
    ci.add_argument(
        "--no-write-github-summary",
        dest="write_github_summary",
        action="store_false",
        help="Do not write summary to GITHUB_STEP_SUMMARY (overrides config)",
    )
    ci.set_defaults(func=handlers.cmd_ci)

    run = subparsers.add_parser("run", help="Run one tool and emit JSON output")
    add_json_flag(run)
    run.add_argument("tool", help="Tool name (pytest, ruff, bandit, etc.)")
    run.add_argument("--repo", default=".", help="Path to repo (default: .)")
    run.add_argument("--workdir", help="Override workdir/subdir")
    run.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for tool outputs (default: .cihub)",
    )
    run.add_argument("--output", help="Override tool output path")
    run.add_argument(
        "--force",
        action="store_true",
        help="Run even if tool is disabled in config",
    )
    run.set_defaults(func=handlers.cmd_run)
