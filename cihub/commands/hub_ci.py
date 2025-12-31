"""Hub production CI helpers."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from importlib import util
from pathlib import Path
from typing import Any

from cihub.cli import hub_root
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


def _write_outputs(values: dict[str, str], output_path: Path | None) -> None:
    if output_path is None:
        for key, value in values.items():
            print(f"{key}={value}")
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _append_summary(text: str, summary_path: Path | None) -> None:
    if summary_path is None:
        print(text)
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def _resolve_output_path(path_value: str | None, github_output: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_output:
        env_path = os.environ.get("GITHUB_OUTPUT")
        return Path(env_path) if env_path else None
    return None


def _resolve_summary_path(path_value: str | None, github_summary: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_summary:
        env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        return Path(env_path) if env_path else None
    return None


def _run_command(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )


def _load_script_module(module_name: str, path: Path) -> Any:
    spec = util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module at {path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _extract_count(line: str, emoji: str) -> int:
    match = re.search(rf"{re.escape(emoji)}\s*(\d+)", line)
    if match:
        return int(match.group(1))
    return 0


def cmd_mutmut(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "mutmut-run.log"

    proc = _run_command(["mutmut", "run"], workdir)
    log_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode != 0:
        print("::error::mutmut run failed - check for import errors or test failures")
        return EXIT_FAILURE

    log_text = log_path.read_text(encoding="utf-8")
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

    killed = _extract_count(final_line, "🎉")
    survived = _extract_count(final_line, "🙁")
    timeout = _extract_count(final_line, "⏰")
    suspicious = _extract_count(final_line, "🤔")
    skipped = _extract_count(final_line, "🔇")

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


def cmd_bandit(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    cmd = [
        "bandit",
        "-r",
        *args.paths,
        "-f",
        "json",
        "-o",
        str(output_path),
        "--severity-level",
        args.severity,
        "--confidence-level",
        args.confidence,
    ]
    _run_command(cmd, Path("."))

    high = 0
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            results = data.get("results", []) if isinstance(data, dict) else []
            high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
        except json.JSONDecodeError:
            high = 0

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    _append_summary(f"## Bandit SAST\nHigh severity: {high}\n", summary_path)

    if high > 0:
        subprocess.run(  # noqa: S603
            ["bandit", "-r", *args.paths, "--severity-level", "high"],  # noqa: S607
            text=True,
        )
        print(f"::error::Found {high} high-severity issues")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def _count_pip_audit_vulns(data: Any) -> int:
    if not isinstance(data, list):
        return 0
    total = 0
    for item in data:
        vulns = item.get("vulns") or item.get("vulnerabilities") or []
        total += len(vulns)
    return total


def cmd_pip_audit(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    cmd = [
        "pip-audit",
        *sum([["-r", req] for req in args.requirements], []),
        "--format",
        "json",
        "--output",
        str(output_path),
    ]
    _run_command(cmd, Path("."))

    vulns = 0
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            vulns = _count_pip_audit_vulns(data)
        except json.JSONDecodeError:
            vulns = 0

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    _append_summary(
        f"## Dependency Vulnerabilities\nFound: {vulns}\n",
        summary_path,
    )

    if vulns > 0:
        markdown = subprocess.run(  # noqa: S603
            ["pip-audit", "--format", "markdown"],  # noqa: S607
            text=True,
            capture_output=True,
        )
        if markdown.stdout:
            _append_summary(markdown.stdout, summary_path)
        print(f"::error::Found {vulns} dependency vulnerabilities")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def cmd_zizmor_check(args: argparse.Namespace) -> int:
    sarif_path = Path(args.sarif)
    if not sarif_path.exists():
        print(f"::error::SARIF file not found: {sarif_path}")
        return EXIT_FAILURE

    high = 0
    try:
        sarif = json.loads(sarif_path.read_text(encoding="utf-8"))
        runs = sarif.get("runs", []) if isinstance(sarif, dict) else []
        if runs:
            results = runs[0].get("results", []) or []
            high = len([r for r in results if r.get("level") in ("error", "warning")])
    except json.JSONDecodeError:
        high = 0

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    _append_summary(
        f"## Zizmor Workflow Security\nHigh/Warning findings: {high}\n",
        summary_path,
    )

    if high > 0:
        print("::error::Found workflow security findings - review in Security tab")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def cmd_validate_configs(args: argparse.Namespace) -> int:
    root = hub_root()
    configs_dir = Path(args.configs_dir) if args.configs_dir else root / "config" / "repos"
    script_path = root / "scripts" / "load_config.py"
    if not script_path.exists():
        print(f"Missing script: {script_path}", file=sys.stderr)
        return EXIT_FAILURE

    module = _load_script_module("load_config", script_path)
    load_config = module.load_config
    generate_workflow_inputs = module.generate_workflow_inputs

    for config_path in sorted(configs_dir.glob("*.yaml")):
        repo = config_path.stem
        print(f"Validating {repo}")
        config = load_config(repo_name=repo, hub_root=root)
        generate_workflow_inputs(config)

    print("✓ All configs valid")
    return EXIT_SUCCESS


def cmd_validate_profiles(args: argparse.Namespace) -> int:
    root = hub_root()
    profiles_dir = Path(args.profiles_dir) if args.profiles_dir else root / "templates" / "profiles"
    try:
        import yaml
    except ImportError as exc:
        print(f"Missing PyYAML: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    for path in sorted(profiles_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            print(f"{path} not a dict", file=sys.stderr)
            return EXIT_FAILURE
        print(f"✓ {path.name}")
    return EXIT_SUCCESS


def cmd_license_check(args: argparse.Namespace) -> int:
    proc = _run_command(["pip-licenses", "--format=csv"], Path("."))
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    total = len(lines)
    copyleft = len([line for line in lines if re.search(r"GPL|AGPL", line, re.I)])

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    summary = "## License Check\n"
    summary += f"Total packages: {total}\n"
    summary += f"Copyleft (GPL/AGPL): {copyleft}\n"
    if copyleft > 0:
        summary += "\nCopyleft packages (dev dependencies are acceptable):\n"
        summary += "\n".join([line for line in lines if re.search(r"GPL|AGPL", line, re.I)])
        summary += "\n"
        _append_summary(summary, summary_path)
        print(f"::warning::Found {copyleft} packages with copyleft licenses")
        return EXIT_SUCCESS

    summary += "PASS - no copyleft licenses\n"
    _append_summary(summary, summary_path)
    return EXIT_SUCCESS


def cmd_gitleaks_summary(args: argparse.Namespace) -> int:
    repo_root = Path(".")
    commits = _run_command(["git", "rev-list", "--count", "HEAD"], repo_root).stdout
    files = _run_command(["git", "ls-files"], repo_root).stdout
    commits_count = commits.strip() if commits else "0"
    files_count = str(len(files.splitlines())) if files else "0"
    outcome = args.outcome or os.environ.get("GITLEAKS_OUTCOME", "skipped")
    leak_text = "0" if outcome == "success" else "CHECK LOGS"
    result_text = "PASS" if outcome == "success" else "FAIL"

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    summary = (
        "## Secret Detection (gitleaks)\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| Commits scanned | {commits_count} |\n"
        f"| Files in repo | {files_count} |\n"
        f"| Leaks found | {leak_text} |\n"
        f"| Result | {result_text} |\n"
    )
    _append_summary(summary, summary_path)
    return EXIT_SUCCESS


def _env_result(name: str) -> str:
    return os.environ.get(name, "skipped")


def cmd_summary(args: argparse.Namespace) -> int:
    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    repo = os.environ.get("GH_REPOSITORY", "")
    branch = os.environ.get("GH_REF_NAME", "")
    run_number = os.environ.get("GH_RUN_NUMBER", "")
    event_name = os.environ.get("GH_EVENT_NAME", "")

    def ran(status: str) -> str:
        return "true" if status not in ("skipped", "cancelled") else "false"

    def ok(status: str) -> str:
        return "true" if status == "success" else "false"

    def status_text(status: str) -> str:
        if status == "success":
            return "Passed"
        if status == "skipped":
            return "Skipped"
        return "Failed"

    results = {
        "actionlint": _env_result("RESULT_ACTIONLINT"),
        "zizmor": _env_result("RESULT_ZIZMOR"),
        "ruff": _env_result("RESULT_LINT"),
        "syntax": _env_result("RESULT_SYNTAX"),
        "mypy": _env_result("RESULT_TYPECHECK"),
        "yamllint": _env_result("RESULT_YAMLLINT"),
        "pytest": _env_result("RESULT_UNIT_TESTS"),
        "mutmut": _env_result("RESULT_MUTATION"),
        "bandit": _env_result("RESULT_BANDIT"),
        "pip-audit": _env_result("RESULT_PIP_AUDIT"),
        "gitleaks": _env_result("RESULT_SECRET_SCAN"),
        "trivy": _env_result("RESULT_TRIVY"),
        "templates": _env_result("RESULT_TEMPLATES"),
        "configs": _env_result("RESULT_CONFIGS"),
        "matrix-keys": _env_result("RESULT_MATRIX_KEYS"),
        "licenses": _env_result("RESULT_LICENSE"),
        "dependency-review": _env_result("RESULT_DEP_REVIEW"),
        "scorecard": _env_result("RESULT_SCORECARD"),
    }

    lines = [
        "## Hub Production CI Summary",
        "",
        "### Environment",
        "",
        "| Setting | Value |",
        "|---------|-------|",
        f"| Repository | {repo} |",
        f"| Branch | {branch} |",
        f"| Run Number | #{run_number} |",
        f"| Trigger | {event_name} |",
        "| Language | Python |",
        "",
        "## Tools Enabled",
        "",
        "| Category | Tool | Configured | Ran | Success |",
        "|----------|------|------------|-----|---------|",
        f"| Workflow | actionlint | true | {ran(results['actionlint'])} | {ok(results['actionlint'])} |",
        f"| Workflow | zizmor | true | {ran(results['zizmor'])} | {ok(results['zizmor'])} |",
        f"| Quality | ruff | true | {ran(results['ruff'])} | {ok(results['ruff'])} |",
        f"| Quality | syntax | true | {ran(results['syntax'])} | {ok(results['syntax'])} |",
        f"| Quality | mypy | true | {ran(results['mypy'])} | {ok(results['mypy'])} |",
        f"| Quality | yamllint | true | {ran(results['yamllint'])} | {ok(results['yamllint'])} |",
        f"| Testing | pytest | true | {ran(results['pytest'])} | {ok(results['pytest'])} |",
        f"| Testing | mutmut | true | {ran(results['mutmut'])} | {ok(results['mutmut'])} |",
        f"| Security | bandit | true | {ran(results['bandit'])} | {ok(results['bandit'])} |",
        f"| Security | pip-audit | true | {ran(results['pip-audit'])} | {ok(results['pip-audit'])} |",
        f"| Security | gitleaks | true | {ran(results['gitleaks'])} | {ok(results['gitleaks'])} |",
        f"| Security | trivy | true | {ran(results['trivy'])} | {ok(results['trivy'])} |",
        f"| Validate | templates | true | {ran(results['templates'])} | {ok(results['templates'])} |",
        f"| Validate | configs | true | {ran(results['configs'])} | {ok(results['configs'])} |",
        f"| Validate | matrix-keys | true | {ran(results['matrix-keys'])} | {ok(results['matrix-keys'])} |",
        f"| Validate | licenses | true | {ran(results['licenses'])} | {ok(results['licenses'])} |",
        f"| Supply Chain | dependency-review | true | {ran(results['dependency-review'])} | {ok(results['dependency-review'])} |",  # noqa: E501
        f"| Supply Chain | scorecard | true | {ran(results['scorecard'])} | {ok(results['scorecard'])} |",
        "",
        "### Failed or Skipped Checks",
        "",
        "| Check | Status |",
        "|-------|--------|",
    ]

    has_issues = False
    for name, status in results.items():
        if status != "success":
            has_issues = True
            lines.append(f"| {name} | {status} |")
    if not has_issues:
        lines.append("| None | success |")
    lines.append("")
    lines.extend(
        [
            "### Quality Gates",
            "",
            "| Check | Threshold | Status |",
            "|-------|-----------|--------|",
            f"| Unit Tests | pass | {status_text(results['pytest'])} |",
            f"| Coverage | 70% min | {'Passed' if results['pytest'] == 'success' else 'N/A'} |",
            f"| Mutation Score | 70% min | {status_text(results['mutmut'])} |",
            f"| Type Check (mypy) | 0 errors | {'Passed' if results['mypy'] == 'success' else 'Failed'} |",
            f"| SAST (bandit) | 0 high | {'Passed' if results['bandit'] == 'success' else 'Failed'} |",
            f"| Secrets (gitleaks) | 0 leaks | {'Passed' if results['gitleaks'] == 'success' else 'Failed'} |",
            "",
            "Job summary generated at run-time",
        ]
    )
    _append_summary("\n".join(lines), summary_path)
    return EXIT_SUCCESS


def cmd_enforce(args: argparse.Namespace) -> int:
    checks = [
        ("actionlint", _env_result("RESULT_ACTIONLINT"), "fix workflow syntax"),
        ("zizmor", _env_result("RESULT_ZIZMOR"), "address workflow security findings"),
        ("mypy", _env_result("RESULT_TYPECHECK"), "fix mypy errors"),
        ("yamllint", _env_result("RESULT_YAMLLINT"), "fix config syntax"),
        ("ruff", _env_result("RESULT_LINT"), "fix ruff lint violations"),
        ("syntax", _env_result("RESULT_SYNTAX"), "fix Python syntax errors"),
        ("unit-tests", _env_result("RESULT_UNIT_TESTS"), "unit tests failed"),
        ("mutation-tests", _env_result("RESULT_MUTATION"), "mutation testing failed"),
        ("bandit", _env_result("RESULT_BANDIT"), "security scan failed"),
        ("pip-audit", _env_result("RESULT_PIP_AUDIT"), "dependency audit failed"),
        ("gitleaks", _env_result("RESULT_SECRET_SCAN"), "secret detection failed"),
        ("trivy", _env_result("RESULT_TRIVY"), "trivy scan failed"),
        (
            "validate-templates",
            _env_result("RESULT_TEMPLATES"),
            "template validation failed",
        ),
        ("validate-configs", _env_result("RESULT_CONFIGS"), "config validation failed"),
        (
            "verify-matrix-keys",
            _env_result("RESULT_MATRIX_KEYS"),
            "matrix key validation failed",
        ),
        ("license-check", _env_result("RESULT_LICENSE"), "license compliance failed"),
        (
            "dependency-review",
            _env_result("RESULT_DEP_REVIEW"),
            "dependency review failed",
        ),
        ("scorecard", _env_result("RESULT_SCORECARD"), "scorecard checks failed"),
    ]

    failed = False
    for name, result, message in checks:
        if result in ("failure", "cancelled"):
            print(f"::error::{name} failed - {message}")
            failed = True

    if failed:
        return EXIT_FAILURE
    print("All critical checks passed")
    return EXIT_SUCCESS


def cmd_hub_ci(args: argparse.Namespace) -> int:
    handlers = {
        "ruff": cmd_ruff,
        "black": cmd_black,
        "mutmut": cmd_mutmut,
        "bandit": cmd_bandit,
        "pip-audit": cmd_pip_audit,
        "zizmor-check": cmd_zizmor_check,
        "validate-configs": cmd_validate_configs,
        "validate-profiles": cmd_validate_profiles,
        "license-check": cmd_license_check,
        "gitleaks-summary": cmd_gitleaks_summary,
        "summary": cmd_summary,
        "enforce": cmd_enforce,
    }
    handler = handlers.get(args.subcommand)
    if handler is None:
        print(f"Unknown hub-ci subcommand: {args.subcommand}", file=sys.stderr)
        return EXIT_USAGE
    return handler(args)
