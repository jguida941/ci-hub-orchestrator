#!/usr/bin/env python3
"""
CLI command matrix runner.

Lists and optionally executes core CLI commands with notes about scope,
dependencies, and CI-only requirements.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: list[str]
    category: str
    requires_repo: bool = False
    requires_report: bool = False
    requires_gh: bool = False
    ci_only: bool = False
    mutating: bool = False
    notes: str = ""
    tags: list[str] = field(default_factory=list)


def _build_commands(python_bin: str, repo_path: Path | None, report_path: Path | None) -> list[CommandSpec]:
    repo_arg = str(repo_path) if repo_path else "<repo>"
    report_arg = str(report_path) if report_path else "<report>"

    return [
        CommandSpec(
            name="version",
            argv=[python_bin, "-m", "cihub", "--version"],
            category="local",
        ),
        CommandSpec(
            name="preflight",
            argv=[python_bin, "-m", "cihub", "preflight"],
            category="local",
        ),
        CommandSpec(
            name="detect",
            argv=[python_bin, "-m", "cihub", "detect", "--repo", repo_arg],
            category="local",
            requires_repo=True,
        ),
        CommandSpec(
            name="validate",
            argv=[python_bin, "-m", "cihub", "validate", "--repo", repo_arg],
            category="local",
            requires_repo=True,
        ),
        CommandSpec(
            name="ci",
            argv=[python_bin, "-m", "cihub", "ci", "--repo", repo_arg, "--output-dir", ".cihub"],
            category="local",
            requires_repo=True,
            notes="Uses repo toolchain; may be slow.",
        ),
        CommandSpec(
            name="report-summary",
            argv=[python_bin, "-m", "cihub", "report", "summary", "--report", report_arg],
            category="local",
            requires_report=True,
        ),
        CommandSpec(
            name="check-fast",
            argv=[python_bin, "-m", "cihub", "check"],
            category="local",
            notes="Fast tier (~30s).",
        ),
        CommandSpec(
            name="check-full",
            argv=[python_bin, "-m", "cihub", "check", "--full"],
            category="local",
            notes="Full tier (~3m).",
        ),
        CommandSpec(
            name="docs-generate",
            argv=[python_bin, "-m", "cihub", "docs", "generate"],
            category="local",
        ),
        CommandSpec(
            name="docs-check",
            argv=[python_bin, "-m", "cihub", "docs", "check"],
            category="local",
        ),
        CommandSpec(
            name="verify",
            argv=[python_bin, "-m", "cihub", "verify"],
            category="local",
            notes="Contract and template checks.",
        ),
        CommandSpec(
            name="verify-remote",
            argv=[python_bin, "-m", "cihub", "verify", "--remote"],
            category="remote",
            requires_gh=True,
            notes="Requires GH auth.",
        ),
        CommandSpec(
            name="verify-integration",
            argv=[python_bin, "-m", "cihub", "verify", "--remote", "--integration", "--install-deps"],
            category="remote",
            requires_gh=True,
            mutating=True,
            notes="Clones repos; slow and networked.",
        ),
        CommandSpec(
            name="sync-templates-check",
            argv=[python_bin, "-m", "cihub", "sync-templates", "--check"],
            category="remote",
            requires_gh=True,
            notes="Requires GH token.",
        ),
    ]


def _format_table(rows: Iterable[dict[str, str]]) -> str:
    headers = ["name", "category", "command", "notes"]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for key in headers:
            widths[key] = max(widths[key], len(row.get(key, "")))
    lines = []
    header_line = "  ".join(h.ljust(widths[h]) for h in headers)
    lines.append(header_line)
    lines.append("  ".join("-" * widths[h] for h in headers))
    for row in rows:
        lines.append("  ".join(row.get(h, "").ljust(widths[h]) for h in headers))
    return "\n".join(lines)


def _format_markdown(rows: Iterable[dict[str, str]]) -> str:
    lines = ["| Name | Category | Command | Notes |", "| --- | --- | --- | --- |"]
    for row in rows:
        lines.append(
            f"| {row.get('name', '')} | {row.get('category', '')} | {row.get('command', '')} | {row.get('notes', '')} |"
        )
    return "\n".join(lines)


def _format_rows(commands: list[CommandSpec], repo_path: Path | None, report_path: Path | None) -> list[dict[str, str]]:
    rows = []
    for cmd in commands:
        missing = []
        if cmd.requires_repo and repo_path is None:
            missing.append("--repo")
        if cmd.requires_report and report_path is None:
            missing.append("--report")
        note = cmd.notes
        if missing:
            note = f"{note} Missing {', '.join(missing)}.".strip()
        rows.append(
            {
                "name": cmd.name,
                "category": cmd.category,
                "command": " ".join(cmd.argv),
                "notes": note,
            }
        )
    return rows


def _run_command(cmd: CommandSpec) -> int:
    print(f"[RUN] {' '.join(cmd.argv)}")
    result = subprocess.run(cmd.argv, text=True)  # noqa: S603
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI command matrix runner.")
    parser.add_argument("--repo", type=Path, help="Path to a repo for repo-scoped commands.")
    parser.add_argument("--report", type=Path, help="Path to report.json for report summary.")
    parser.add_argument("--python", dest="python_bin", default=sys.executable, help="Python executable to use.")
    parser.add_argument("--format", choices=["table", "markdown"], default="table", help="Output format.")
    parser.add_argument("--run", action="store_true", help="Execute runnable commands.")
    parser.add_argument("--include-ci-only", action="store_true", help="Include CI-only commands.")
    parser.add_argument("--include-remote", action="store_true", help="Include GH/network-required commands.")
    parser.add_argument("--include-mutating", action="store_true", help="Include mutating commands.")
    parser.add_argument("--only", action="append", default=[], help="Run/list only matching command names.")
    parser.add_argument("--keep-going", action="store_true", help="Continue after failures.")
    args = parser.parse_args()

    repo_path = args.repo.resolve() if args.repo else None
    report_path = args.report.resolve() if args.report else None
    commands = _build_commands(args.python_bin, repo_path, report_path)

    if args.only:
        wanted = set(args.only)
        commands = [cmd for cmd in commands if cmd.name in wanted]

    if not args.run:
        rows = _format_rows(commands, repo_path, report_path)
        if args.format == "markdown":
            print(_format_markdown(rows))
        else:
            print(_format_table(rows))
        return 0

    exit_code = 0
    for cmd in commands:
        if cmd.ci_only and not args.include_ci_only:
            print(f"[SKIP] {cmd.name}: CI-only")
            continue
        if cmd.requires_gh and not args.include_remote:
            print(f"[SKIP] {cmd.name}: requires GH auth/network")
            continue
        if cmd.mutating and not args.include_mutating:
            print(f"[SKIP] {cmd.name}: mutating")
            continue
        if cmd.requires_repo and repo_path is None:
            print(f"[SKIP] {cmd.name}: missing --repo")
            continue
        if cmd.requires_report and report_path is None:
            print(f"[SKIP] {cmd.name}: missing --report")
            continue

        status = _run_command(cmd)
        if status != 0:
            exit_code = status
            if not args.keep_going:
                break

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
