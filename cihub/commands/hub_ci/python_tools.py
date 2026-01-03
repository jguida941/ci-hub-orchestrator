"""Python linting and mutation testing commands."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS

from . import (
    _append_summary,
    _extract_count,
    _resolve_output_path,
    _resolve_summary_path,
    _run_command,
    _write_outputs,
)


def cmd_ruff(args: argparse.Namespace) -> int:
    cmd = ["ruff", "check", args.path]
    if args.force_exclude:
        cmd.append("--force-exclude")

    json_proc = _run_command(cmd + ["--output-format=json"], Path("."))
    issues = 0
    try:
        data = json.loads(json_proc.stdout or "[]")
        issues = len(data) if isinstance(data, list) else 0
    except json.JSONDecodeError:
        issues = 0

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues)}, output_path)

    github_proc = subprocess.run(  # noqa: S603
        cmd + ["--output-format=github"],
        text=True,
    )
    return EXIT_SUCCESS if github_proc.returncode == 0 else EXIT_FAILURE


def cmd_black(args: argparse.Namespace) -> int:
    proc = _run_command(["black", "--check", args.path], Path("."))
    output = (proc.stdout or "") + (proc.stderr or "")
    issues = len(re.findall(r"would reformat", output))
    if proc.returncode != 0 and issues == 0:
        issues = 1
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues)}, output_path)
    return EXIT_SUCCESS


def cmd_mutmut(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "mutmut-run.log"

    proc = _run_command(["mutmut", "run"], workdir)
    log_text = (proc.stdout or "") + (proc.stderr or "")
    log_path.write_text(log_text, encoding="utf-8")
    if proc.returncode != 0:
        print("::error::mutmut run failed - check for import errors or test failures")
        print(log_text)  # Print log to help debug CI failures
        return EXIT_FAILURE
    if "mutations/second" not in log_text:
        print("::error::mutmut did not complete successfully")
        print(log_text)
        return EXIT_FAILURE

    final_line = ""
    for line in log_text.splitlines():
        if re.search(r"\d+/\d+", line):
            final_line = line
    if not final_line:
        print("::error::mutmut output missing final counts")
        return EXIT_FAILURE

    killed = _extract_count(final_line, "\U0001f389")
    survived = _extract_count(final_line, "\U0001f641")
    timeout = _extract_count(final_line, "\u23f0")
    suspicious = _extract_count(final_line, "\U0001f914")
    skipped = _extract_count(final_line, "\U0001f507")

    tested = killed + survived + timeout + suspicious
    if tested == 0:
        print("::error::No mutants were tested - check test coverage")
        return EXIT_FAILURE

    score = (killed * 100) // tested

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(
        {
            "mutation_score": str(score),
            "killed": str(killed),
            "survived": str(survived),
            "timeout": str(timeout),
            "suspicious": str(suspicious),
        },
        output_path,
    )

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    summary = (
        "## Mutation Testing\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| **Score** | **{score}%** |\n"
        f"| Killed | {killed} |\n"
        f"| Survived | {survived} |\n"
        f"| Timeout | {timeout} |\n"
        f"| Suspicious | {suspicious} |\n"
        f"| Skipped | {skipped} |\n"
        f"| Total Tested | {tested} |\n"
    )
    if score < args.min_score:
        summary += f"\n**FAILED**: Score {score}% below {args.min_score}% threshold\n"
        _append_summary(summary, summary_path)
        print(f"::error::Mutation score {score}% below {args.min_score}% threshold")
        print(log_text)
        return EXIT_FAILURE
    summary += f"\n**PASSED**: Score {score}% meets {args.min_score}% threshold\n"
    _append_summary(summary, summary_path)
    return EXIT_SUCCESS
